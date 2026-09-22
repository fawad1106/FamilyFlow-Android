import base64, hashlib, hmac, secrets, sqlite3
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Cookie, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE=Path(__file__).resolve().parents[2]
FRONT=BASE/"frontend"
DB=BASE/"database"/"lifeos.db"
UPLOADS=BASE/"database"/"uploads"

def conn():
    DB.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c

def init_db():
    with conn() as d:
        d.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,name TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',color TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,completed INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,due_date TEXT,user_id INTEGER,project_id INTEGER,tags TEXT NOT NULL DEFAULT '',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL);
        CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,title TEXT NOT NULL,content TEXT NOT NULL DEFAULT '',tags TEXT NOT NULL DEFAULT '',project_id INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL);
        CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,name TEXT NOT NULL,stored_name TEXT UNIQUE NOT NULL,size INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        """)
        cols={r["name"] for r in d.execute("PRAGMA table_info(tasks)")}
        for name,sql in [("due_date","ALTER TABLE tasks ADD COLUMN due_date TEXT"),("user_id","ALTER TABLE tasks ADD COLUMN user_id INTEGER"),("project_id","ALTER TABLE tasks ADD COLUMN project_id INTEGER"),("tags","ALTER TABLE tasks ADD COLUMN tags TEXT NOT NULL DEFAULT ''")]:
            if name not in cols:d.execute(sql)
        d.commit()

def phash(p):
    salt=secrets.token_bytes(16); key=hashlib.scrypt(p.encode(),salt=salt,n=16384,r=8,p=1)
    return base64.b64encode(salt+b"."+key).decode()
def pcheck(p,s):
    try:
        raw=base64.b64decode(s); salt,key=raw.split(b".",1)
        return hmac.compare_digest(key,hashlib.scrypt(p.encode(),salt=salt,n=16384,r=8,p=1))
    except Exception:return False
def session(uid):
    t=secrets.token_urlsafe(32)
    with conn() as d:d.execute("INSERT INTO sessions(token,user_id) VALUES(?,?)",(t,uid));d.commit()
    return t
def user(cookie):
    if not cookie: return None
    with conn() as d:return d.execute("SELECT u.id,u.username,u.created_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?",(cookie,)).fetchone()
def need(cookie):
    u=user(cookie)
    if not u:raise HTTPException(401,"Please log in.")
    return u
def clean_tags(x):return ",".join(dict.fromkeys(t.strip() for t in x.split(",") if t.strip()))

class Cred(BaseModel):username:str=Field(min_length=3,max_length=40);password:str=Field(min_length=8,max_length=128)
class TaskIn(BaseModel):title:str=Field(min_length=1,max_length=200);due_date:str|None=None;project_id:int|None=None;tags:str=""
class ProjectIn(BaseModel):name:str=Field(min_length=1,max_length=120);description:str="";color:str=""
class NoteIn(BaseModel):title:str=Field(min_length=1,max_length=200);content:str="";tags:str="";project_id:int|None=None

@asynccontextmanager
async def lifespan(app):init_db();yield
app=FastAPI(title="LifeOS",version="1.0.0",lifespan=lifespan)
app.mount("/css",StaticFiles(directory=FRONT/"css"),name="css");app.mount("/js",StaticFiles(directory=FRONT/"js"),name="js")

@app.get("/")
def home():return FileResponse(FRONT/"index.html")
@app.get("/health")
def health():return {"status":"ok","project":"life-os","version":"1.0.0"}

@app.post("/api/auth/register")
def register(x:Cred,response:Response):
    name=x.username.strip().lower()
    with conn() as d:
        if d.execute("SELECT 1 FROM users WHERE username=?",(name,)).fetchone():raise HTTPException(409,"Username already exists.")
        uid=d.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",(name,phash(x.password))).lastrowid
        d.execute("UPDATE tasks SET user_id=? WHERE user_id IS NULL",(uid,));d.commit()
    response.set_cookie("lifeos_session",session(uid),httponly=True,samesite="lax",max_age=2592000)
    return {"id":uid,"username":name}
@app.post("/api/auth/login")
def login(x:Cred,response:Response):
    name=x.username.strip().lower()
    with conn() as d:u=d.execute("SELECT * FROM users WHERE username=?",(name,)).fetchone()
    if not u or not pcheck(x.password,u["password_hash"]):raise HTTPException(401,"Invalid username or password.")
    response.set_cookie("lifeos_session",session(u["id"]),httponly=True,samesite="lax",max_age=2592000)
    return {"id":u["id"],"username":u["username"]}
@app.post("/api/auth/logout")
def logout(response:Response,lifeos_session:str|None=Cookie(default=None)):
    if lifeos_session:
        with conn() as d:d.execute("DELETE FROM sessions WHERE token=?",(lifeos_session,));d.commit()
    response.delete_cookie("lifeos_session");return {"ok":True}
@app.get("/api/auth/me")
def me(lifeos_session:str|None=Cookie(default=None)):return dict(need(lifeos_session))

def taskrow(r):return {"id":r["id"],"title":r["title"],"completed":bool(r["completed"]),"created_at":r["created_at"],"due_date":r["due_date"],"project_id":r["project_id"],"tags":r["tags"]}
@app.get("/api/tasks")
def tasks(q:str="",lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:rows=d.execute("SELECT * FROM tasks WHERE user_id=? AND (title LIKE ? OR tags LIKE ?) ORDER BY completed,CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,due_date,id DESC",(u["id"],f"%{q}%",f"%{q}%")).fetchall()
    return [taskrow(r) for r in rows]
@app.post("/api/tasks")
def task_create(x:TaskIn,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session);title=x.title.strip()
    if not title:raise HTTPException(400,"Task title cannot be empty.")
    with conn() as d:
        if x.project_id and not d.execute("SELECT 1 FROM projects WHERE id=? AND user_id=?",(x.project_id,u["id"])).fetchone():raise HTTPException(404,"Project not found.")
        cur=d.execute("INSERT INTO tasks(title,due_date,project_id,tags,user_id) VALUES(?,?,?,?,?)",(title,x.due_date,x.project_id,clean_tags(x.tags),u["id"]));r=d.execute("SELECT * FROM tasks WHERE id=?",(cur.lastrowid,)).fetchone();d.commit()
    return taskrow(r)
@app.patch("/api/tasks/{tid}")
def task_update(tid:int,x:TaskIn,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:
        if not d.execute("SELECT 1 FROM tasks WHERE id=? AND user_id=?",(tid,u["id"])).fetchone():raise HTTPException(404,"Task not found.")
        d.execute("UPDATE tasks SET title=?,due_date=?,project_id=?,tags=? WHERE id=? AND user_id=?",(x.title.strip(),x.due_date,x.project_id,clean_tags(x.tags),tid,u["id"]));r=d.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone();d.commit()
    return taskrow(r)
@app.patch("/api/tasks/{tid}/complete")
def task_complete(tid:int,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:d.execute("UPDATE tasks SET completed=1 WHERE id=? AND user_id=?",(tid,u["id"]));r=d.execute("SELECT * FROM tasks WHERE id=? AND user_id=?",(tid,u["id"])).fetchone();d.commit()
    if not r:raise HTTPException(404,"Task not found.")
    return taskrow(r)
@app.delete("/api/tasks/{tid}",status_code=204)
def task_delete(tid:int,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:c=d.execute("DELETE FROM tasks WHERE id=? AND user_id=?",(tid,u["id"]));d.commit()
    if not c.rowcount:raise HTTPException(404,"Task not found.")

@app.get("/api/projects")
def projects(lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:rows=d.execute("SELECT p.*,COUNT(t.id) task_count,COALESCE(SUM(t.completed),0) done_count FROM projects p LEFT JOIN tasks t ON t.project_id=p.id WHERE p.user_id=? GROUP BY p.id ORDER BY p.id DESC",(u["id"],)).fetchall()
    return [dict(r) for r in rows]
@app.post("/api/projects")
def project_create(x:ProjectIn,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:cur=d.execute("INSERT INTO projects(user_id,name,description,color) VALUES(?,?,?,?)",(u["id"],x.name.strip(),x.description,x.color));d.commit()
    return {"id":cur.lastrowid,**x.model_dump()}
@app.patch("/api/projects/{pid}")
def project_update(pid:int,x:ProjectIn,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:c=d.execute("UPDATE projects SET name=?,description=?,color=? WHERE id=? AND user_id=?",(x.name.strip(),x.description,x.color,pid,u["id"]));d.commit()
    if not c.rowcount:raise HTTPException(404,"Project not found.")
    return {"id":pid,**x.model_dump()}
@app.delete("/api/projects/{pid}",status_code=204)
def project_delete(pid:int,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:c=d.execute("DELETE FROM projects WHERE id=? AND user_id=?",(pid,u["id"]));d.commit()
    if not c.rowcount:raise HTTPException(404,"Project not found.")

@app.get("/api/notes")
def notes(q:str="",lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:rows=d.execute("SELECT * FROM notes WHERE user_id=? AND (title LIKE ? OR content LIKE ? OR tags LIKE ?) ORDER BY updated_at DESC",(u["id"],f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
    return [dict(r) for r in rows]
@app.post("/api/notes")
def note_create(x:NoteIn,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:cur=d.execute("INSERT INTO notes(user_id,title,content,tags,project_id) VALUES(?,?,?,?,?)",(u["id"],x.title.strip(),x.content,clean_tags(x.tags),x.project_id));r=d.execute("SELECT * FROM notes WHERE id=?",(cur.lastrowid,)).fetchone();d.commit()
    return dict(r)
@app.patch("/api/notes/{nid}")
def note_update(nid:int,x:NoteIn,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:c=d.execute("UPDATE notes SET title=?,content=?,tags=?,project_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",(x.title.strip(),x.content,clean_tags(x.tags),x.project_id,nid,u["id"]));r=d.execute("SELECT * FROM notes WHERE id=?",(nid,)).fetchone();d.commit()
    if not c.rowcount:raise HTTPException(404,"Note not found.")
    return dict(r)
@app.delete("/api/notes/{nid}",status_code=204)
def note_delete(nid:int,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:c=d.execute("DELETE FROM notes WHERE id=? AND user_id=?",(nid,u["id"]));d.commit()
    if not c.rowcount:raise HTTPException(404,"Note not found.")

@app.get("/api/dashboard/stats")
def stats(lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:
        t=d.execute("SELECT COUNT(*) total,COALESCE(SUM(completed),0) done FROM tasks WHERE user_id=?",(u["id"],)).fetchone()
        p=d.execute("SELECT COUNT(*) n FROM projects WHERE user_id=?",(u["id"],)).fetchone()
        n=d.execute("SELECT COUNT(*) n FROM notes WHERE user_id=?",(u["id"],)).fetchone()
        f=d.execute("SELECT COUNT(*) n FROM files WHERE user_id=?",(u["id"],)).fetchone()
    return {"tasks":t["total"],"completed_tasks":t["done"],"projects":p["n"],"notes":n["n"],"files":f["n"]}

@app.get("/api/search")
def search(q:str,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session);z=f"%{q}%"
    with conn() as d:
        a=d.execute("SELECT id,title,'task' type FROM tasks WHERE user_id=? AND (title LIKE ? OR tags LIKE ?) LIMIT 20",(u["id"],z,z)).fetchall()
        b=d.execute("SELECT id,name title,'project' type FROM projects WHERE user_id=? AND (name LIKE ? OR description LIKE ?) LIMIT 20",(u["id"],z,z)).fetchall()
        c=d.execute("SELECT id,title,'note' type FROM notes WHERE user_id=? AND (title LIKE ? OR content LIKE ? OR tags LIKE ?) LIMIT 20",(u["id"],z,z,z)).fetchall()
    return [dict(x) for x in [*a,*b,*c]]

@app.get("/api/files")
def file_list(lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:rows=d.execute("SELECT * FROM files WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall()
    return [dict(r) for r in rows]
@app.post("/api/files")
async def file_upload(file:UploadFile=File(...),lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session);UPLOADS.mkdir(parents=True,exist_ok=True);name=Path(file.filename or "file").name;stored=secrets.token_hex(16)+"_"+name;data=await file.read();(UPLOADS/stored).write_bytes(data)
    with conn() as d:cur=d.execute("INSERT INTO files(user_id,name,stored_name,size) VALUES(?,?,?,?)",(u["id"],name,stored,len(data)));d.commit()
    return {"id":cur.lastrowid,"name":name,"size":len(data)}
@app.get("/api/files/{fid}")
def file_get(fid:int,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:r=d.execute("SELECT * FROM files WHERE id=? AND user_id=?",(fid,u["id"])).fetchone()
    if not r:raise HTTPException(404,"File not found.")
    p=UPLOADS/r["stored_name"]
    if not p.exists():raise HTTPException(404,"Stored file missing.")
    return FileResponse(p,filename=r["name"])
@app.delete("/api/files/{fid}",status_code=204)
def file_delete(fid:int,lifeos_session:str|None=Cookie(default=None)):
    u=need(lifeos_session)
    with conn() as d:r=d.execute("SELECT * FROM files WHERE id=? AND user_id=?",(fid,u["id"])).fetchone()
    if not r:raise HTTPException(404,"File not found.")
    p=UPLOADS/r["stored_name"]
    if p.exists():p.unlink()
    with conn() as d:d.execute("DELETE FROM files WHERE id=?",(fid,));d.commit()
