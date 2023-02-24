import os
from fastapi import FastAPI, Request, HTTPException
import motor.motor_asyncio
import pydantic
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "https://ecse-three-led.netlify.app",
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


@app.put("/api/state")
async def set_state(request: Request):
  state_request = await request.json()
  user = request.headers["X-API-Key"]
  
  await db["state"].update_one({"user": user}, {"$set": state_request}, upsert=True)
  
  if updated_state := await db["state"].find_one({"user": user}):
    return updated_state
  else: 
    raise HTTPException(status_code=404, detail="Item not found")

@app.get("/api/state")
async def get_state(request: Request):
  user = request.headers["X-API-Key"]
  state = await db["state"].find_one({"user": user})
  if state == None:
    return {
      "light_switch_1": False,
      "light_switch_2": False,
      "light_switch_3": False
    }
  return state