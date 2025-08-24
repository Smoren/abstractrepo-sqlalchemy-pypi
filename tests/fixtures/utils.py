import pickle
from typing import List, Union

from pydantic import BaseModel


def dumps(data: Union[List[BaseModel], BaseModel]) -> bytes:
    if isinstance(data, list):
        return pickle.dumps([item.__dict__ for item in data])
    return pickle.dumps(data.__dict__)
