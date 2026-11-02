# Auto-register all javascript / typescript route extractors
from . import express
from . import nestjs
from . import fastify
from . import nextjs

__all__ = ["express", "nestjs", "fastify", "nextjs"]
