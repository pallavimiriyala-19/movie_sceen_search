from typing import List
from pydantic import BaseModel

class SceneActor(BaseModel):
    scene_id: int
    name: str
    confidence: float
    frame_path: str

class Actor(BaseModel):
    actor_id: int
    name: str
