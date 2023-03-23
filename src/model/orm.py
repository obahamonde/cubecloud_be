"""Lightweight ORM to perform simple CRUD operations on FaunaDB collections and provision indexes
   the fauna query object is available also within the class for further customization
"""
from __future__ import annotations
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from faunadb import query as q
from faunadb.objects import Query
from faunadb.client import FaunaClient
from faunadb.errors import NotFound, BadRequest
from src.config import env
from src.utils import gen_oid, gen_now


class FaunaModel(BaseModel):
    """FaunaDB Model"""
    oid: str = Field(default_factory=gen_oid, alias="id", index=True, unique=True)
    created_at:str = Field(default_factory=gen_now, alias="createdAt")
    
    @classmethod
    def client(cls)->FaunaClient:
        """Return a FaunaClient"""
        return FaunaClient(secret=env.FAUNA_SECRET)
    
    @classmethod
    def q(cls)->Query:
        """Return a FaunaDB query"""
        return cls.client().query
    
    @classmethod
    def provision(cls)->None:
        """Provision the collection and indexes"""
        _q = cls.q()
        try:
            if not _q(q.exists(q.collection(cls.__name__.lower()))):
                _q(q.create_collection({"name": cls.__name__.lower()}))
                print(f"Created collection {cls.__name__.lower()}")
                _q(q.create_index({
                    "name": cls.__name__.lower(),
                    "source": q.collection(cls.__name__.lower())
                }))
                print(f"Created index {cls.__name__.lower()}")
            for field in cls.__fields__.values():
                if field.field_info.extra.get("index"):
                    _q(q.create_index({
                        "name": f"{cls.__name__.lower()}_{field.name}",
                        "source": q.collection(cls.__name__.lower()),
                        "terms": [{"field": ["data", field.name]}]
                    }))
                    print(f"Created index {cls.__name__.lower()}_{field.name}")
                if field.field_info.extra.get("unique"):
                    _q(q.create_index({
                        "name": f"{cls.__name__.lower()}_{field.name}_unique",
                        "source": q.collection(cls.__name__.lower()),
                        "terms": [{"field": ["data", field.name]}],
                        "unique": True
                    }))
                    print(f"Created unique index {cls.__name__.lower()}_{field.name}_unique")
        except BadRequest as exc:
            print(exc)
            
    @classmethod
    def exists(cls, oid:str)->bool:
        """Check if a document exists"""
        return cls.q()(q.exists(q.match(q.index(f"{cls.__name__.lower()}_oid"), oid)))
    
    @classmethod
    def find_unique(cls, field:str, value:Any)->Optional[Dict[str, Any]]:
        """Find a document by a unique field"""
        try:
            return cls.q()(q.get(q.match(q.index(f"{cls.__name__.lower()}_{field}_unique"), value)))["data"]
        except NotFound:
            return None
        
    @classmethod
    def find_many(cls, field:str, value:Any)->List[Dict[str, Any]]:
        """Find documents by a field"""
        ref = cls.q()(q.paginate(q.match(q.index(f"{cls.__name__.lower()}_{field}"), value)))["data"]
        return [cls.q()(q.get(ref))["data"] for ref in ref]
    
    @classmethod
    def find(cls, oid:str)->Optional[Dict[str, Any]]:
        """Find a document by id"""
        try:
            setref =  cls.q()(q.match(q.index(f"{cls.__name__.lower()}_oid_unique"), oid))
            return cls.q()(q.get(setref))["data"]
        except NotFound:
            return None
        
    @classmethod
    def find_all(cls)->List[Dict[str, Any]]:
        """Find all documents"""
        refs = cls.q()(q.paginate(q.match(q.index(cls.__name__.lower()))))["data"]
        return [cls.q()(q.get(ref))["data"] for ref in refs]
    
    @classmethod
    def delete_unique(cls, field:str, value:Any)->bool:
        """Delete a document by a unique field"""
        try:
            ref = cls.q()(q.get(q.match(q.index(f"{cls.__name__.lower()}_{field}_unique"), value)))
            cls.q()(q.delete(ref["ref"]))
            return True
        except NotFound:
            return False
        
    @classmethod
    def delete(cls, oid:str)->bool:
        """Delete a document by id"""
        try:
            ref = cls.q()(q.get(q.match(q.index(f"{cls.__name__.lower()}_oid_unique"), oid)))
            cls.q()(q.delete(ref["ref"]))
            return True
        except NotFound:
            return False
    
    def create(self)->Dict[str, Any]:
        """Create a document"""
        try:
            for field in self.__fields__.values():
                if field.field_info.extra.get("unique"):
                    if self.find_unique(field.name, getattr(self, field.name)):
                        raise ValueError(f"{field.name} must be unique")
            return self.q()(q.create(q.collection(self.__class__.__name__.lower()), {"data": self.dict()}))
        except BadRequest as exc:
            print(exc)
            return {}
        
    def update(self)->Dict[str, Any]:
        """Update a document"""
        _q = self.q()
        try:
            ref = _q(q.get(q.match(q.index(f"{self.__class__.__name__.lower()}_id"), self.oid)))
            return _q(q.update(ref, {"data": self.dict()}))
        except NotFound:
            return {}
        
    def save(self)->Dict[str, Any]:
        """Save a document"""
        try:
            if self.exists(self.oid):
               return self.dict()
            return self.create()["data"]
        except BadRequest as exc:
            print(exc)
            return {}