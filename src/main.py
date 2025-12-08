import pydantic
import typing
import phonenumbers
import fastapi
from redis import asyncio as redis
from pydantic_extra_types import phone_numbers
from starlette import config as config_lib

PhoneNumberType = typing.Annotated[
    typing.Union[str, phonenumbers.PhoneNumber], phone_numbers.PhoneNumberValidator(number_format="E164")
]

app = fastapi.FastAPI(title="Phone Cache", version="1.0.0")
config = config_lib.Config("../.env")

redis_client = redis.Redis(
    host=config("REDIS_HOST", default="localhost"),
    port=config("REDIS_PORT", cast=int, default=6379),
    db=config("REDIS_DB", cast=int, default=0))


class Customer(pydantic.BaseModel):
    address: str
    phone: PhoneNumberType = None  # TODO: store/validate phone as int


async def get_details(phone: PhoneNumberType) -> Customer:
    address = await redis_client.get(phone)
    if not address:
        raise fastapi.HTTPException(status_code=404, detail="Phone not found")

    return Customer(address=address, phone=phone)


@app.get("/{phone}", response_model=Customer, responses={404: {}})
async def get(phone: PhoneNumberType):
    return await get_details(phone)


@app.post("/", status_code=201)
async def post(customer: Customer) -> Customer:
    stored = await redis_client.setnx(customer.phone, customer.address)
    if not stored:
        raise fastapi.HTTPException(status_code=409, detail="Duplicate entry")

    return customer


@app.put("/{phone}", responses={404: {}})
async def post(phone: PhoneNumberType, customer: Customer) -> Customer:
    updated = await redis_client.set(phone, customer.address, xx=True)
    if not updated:
        raise fastapi.HTTPException(status_code=404, detail="Phone not found")

    return Customer(phone=phone, address=customer.address)


@app.delete("/{phone}")
async def post(phone: PhoneNumberType) -> Customer:
    details = await get_details(phone)
    await redis_client.delete(phone)

    return details
