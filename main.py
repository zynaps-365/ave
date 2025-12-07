import typing
import phonenumbers
import fastapi
from redis import asyncio as redis
from pydantic_extra_types.phone_numbers import PhoneNumberValidator
from pydantic import BaseModel
from starlette import config as config_lib

PhoneNumberType = typing.Annotated[
    typing.Union[str, phonenumbers.PhoneNumber], PhoneNumberValidator(number_format="E164")
]

app = fastapi.FastAPI()
config = config_lib.Config(".env")

redis_client = redis.Redis(
    host=config("REDIS_HOST", default="localhost"),
    port=config("REDIS_PORT", cast=int, default=6379),
    db=config("REDIS_DB", default="ave"))


class Details(BaseModel):
    address: str


async def get_details(phone: PhoneNumberType) -> Details:
    address = await redis_client.get(phone)
    if not address:
        raise fastapi.HTTPException(status_code=404, detail="Phone not found")

    return Details(address=address)


@app.get("/", response_model=Details, responses={404: {}})
async def get(phone: PhoneNumberType):
    return await get_details(phone)


@app.post("/", status_code=201)
async def post(phone: PhoneNumberType, address) -> Details:
    response = await redis_client.setnx(phone, address)
    if not response:
        raise fastapi.HTTPException(status_code=409, detail="Duplicate entry")

    return Details(address=address)


@app.patch("/", responses={404: {}})
async def post(phone: PhoneNumberType, address) -> Details:
    updated = await redis_client.set(phone, address, xx=True)
    if not updated:
        raise fastapi.HTTPException(status_code=404, detail="Phone not found")

    return Details(address=address)


@app.delete("/")
async def post(phone: PhoneNumberType) -> Details:
    details = await get_details(phone)
    await redis_client.delete(phone)

    return details
