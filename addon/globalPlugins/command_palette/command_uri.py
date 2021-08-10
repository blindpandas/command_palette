# coding: utf-8

import typing as t
import uritools
from dataclasses import dataclass, field
from logHandler import log


@dataclass
class CommandUri:
    format: str
    path: str
    primary_args: t.Dict[str, t.Union[str, int]]
    secondary_args: t.Dict[t.Any, t.Any] = field(default_factory=dict)
    scheme: t.ClassVar = "command"

    @classmethod
    def from_uri_string(cls, uri_string):
        """Return a populated instance of this class or raise ValueError."""
        if not uritools.isuri(uri_string):
            raise ValueError(f"Invalid uri string {uri_string}")
        try:
            parsed = uritools.urisplit(uri_string)
        except Exception as e:
            raise ValueError(f"Could not parse uri {uri_string}") from e
        return cls(
            format=parsed.authority,
            path=uritools.uridecode(parsed.path).lstrip("/"),
            primary_args=cls._unwrap_args(parsed.getquerydict()),
        )

    def to_uri_string(self):
        return uritools.uricompose(
            scheme=self.scheme,
            authority=self.format,
            path=f"/{str(self.path)}",
            query=self.primary_args,
        )

    @classmethod
    def try_parse(cls, uri_string):
        try:
            return cls.from_uri_string(uri_string)
        except:
            log.exception(f"Failed to parse command uri: {uri_string}", exc_info=True)
            return

    def to_bare_uri_string(self):
        return uritools.uricompose(
            scheme=self.scheme,
            authority=self.format,
            path=f"/{str(self.path)}",
        )

    def create_copy(self, format=None, path=None, primary_args=None, secondary_args=None):
        return CommandUri(
            format=format or self.format,
            path=path or self.path,
            primary_args=self.primary_args | (primary_args or {}),
            secondary_args=self.secondary_args | (secondary_args or {}),
        )

    def is_equal_without_primary_args(self, other):
        return self.to_bare_uri_string() == other.to_bare_uri_string()

    def __hash__(self):
        return hash(self.to_uri_string())

    def __str__(self):
        return self.to_uri_string()

    def __repr__(self):
        return f"CommandUri(format='{self.format}', path='{self.path}', primary_args={self.primary_args})"

    def __eq__(self, other):
        if not isinstance(other, CommandUri):
            return NotImplemented
        return self.to_uri_string() == other.to_uri_string()

    @classmethod
    def _unwrap_args(cls, query_dict):
        retval = {}
        for name, valuelist in query_dict.items():
            retval[name] = valuelist[0]
        return retval
