from datetime import datetime
from sqlalchemy import BigInteger, Integer
from sqlalchemy.dialects.mysql import TIMESTAMP, TEXT, VARCHAR, LONGTEXT, BIGINT
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql import func
from typing import Annotated


MyBigInteger = BigInteger()
MyBigInteger = MyBigInteger.with_variant(Integer, "sqlite")
MyBigInteger = MyBigInteger.with_variant(BIGINT(unsigned=True), "mysql")

MyLongText = LONGTEXT()
MyLongText = MyLongText.with_variant(TEXT, "sqlite")


big_int = Annotated[int, mapped_column(MyBigInteger)]
big_intpk = Annotated[int, mapped_column(MyBigInteger, primary_key=True)]
datetime_default_now = Annotated[
    datetime, mapped_column(TIMESTAMP, default=datetime.now, server_default=func.now())
]
intpk = Annotated[int, mapped_column(primary_key=True)]
longtext = Annotated[str, mapped_column(MyLongText)]
text = Annotated[str, mapped_column(TEXT)]
timestamp = Annotated[datetime, mapped_column(TIMESTAMP)]
varchar = Annotated[str, mapped_column(VARCHAR(255))]
