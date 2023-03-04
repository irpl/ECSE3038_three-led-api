import os
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from typing import List
import motor.motor_asyncio
import pydantic
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
  "http://localhost:5500",
  "https://ecse-three-led-v2.netlify.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"])
db = client.switch

pydantic.json.ENCODERS_BY_TYPE[ObjectId]=str

class ConnectionManager:
  def __init__(self):
    self.connections: List[WebSocket] = []

  async def connect(self, websocket: WebSocket):
    await websocket.accept()
    self.connections.append(websocket)

  # todo remove websocket from connections list on close
  async def disconnect(self, websocket: WebSocket):
    self.connections.remove(websocket)

  async def broadcast(self, data: dict):
    for connection in self.connections:
      await connection.send_json(data)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
  await manager.connect(websocket)
  try:
    while True:
      data = await websocket.receive_json()
      await websocket.send_json(data)
  except WebSocketDisconnect:
      await manager.disconnect(websocket)

def helper(data) -> dict:
    data["_id"] = str(data["_id"])
    return data

@app.put("/api/state")
async def set_state(request: Request):
  try:
    state_request = await request.json()
  except:
    raise HTTPException(status_code=400, detail="No JSON body found")
  try:
    user = request.headers["X-API-Key"]
  except KeyError:
    raise HTTPException(status_code=400, detail="No API Key provided")
  
  await db["state"].update_one({"user": user}, {"$set": state_request}, upsert=True)
  
  if updated_state := await db["state"].find_one({"user": user}):
    await manager.broadcast(helper(updated_state))
    return updated_state
  else: 
    raise HTTPException(status_code=404, detail="Item not found")

@app.get("/api/state")
async def get_state(request: Request):
  try:
    user = request.headers["X-API-Key"]
  except KeyError:
    raise HTTPException(status_code=400, detail="No API Key provided")
  
  state = await db["state"].find_one({"user": user})
  if state == None:
    raise HTTPException(status_code=404, detail="No user found with that username")
  return state