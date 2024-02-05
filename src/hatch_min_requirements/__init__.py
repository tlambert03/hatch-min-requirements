"""Hatchling plugin to create optional-dependencies pinned to minimum versions.

Copyright (c) 2023, Talley Lambert

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from __future__ import annotations

import os
import platform
import sys
from importlib import metadata
from typing import TYPE_CHECKING

from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl
from parsley import ParseError, makeGrammar

if TYPE_CHECKING:
    from typing import Callable, Literal, TypeAlias

    from parsley import _GrammarWrapper

    # version_cmp   = wsp* <'<=' | '<' | '!=' | '==' | '>=' | '>' | '~=' | '==='>
    VersionCmp: TypeAlias = Literal["<=", "<", "!=", "==", ">=", ">", "~=", "==="]
    # version       = wsp* <( letterOrDigit | '-' | '_' | '.' | '*' | '+' | '!' )+>
    VersionStr: TypeAlias = str
    # version_one   = version_cmp:op version:v wsp* -> (op, v)
    VersionOne = tuple[VersionCmp, VersionStr]

try:
    __version__ = metadata.version("hatch-min-requirements")
except metadata.PackageNotFoundError:
    __version__ = "uninstalled"
__author__ = "Talley Lambert"

__all__ = ("MinRequirementsMetadataHook", "parse_requirements")


class MinRequirementsMetadataHook(MetadataHookInterface):
    """Hatchling metadata hook to populate optional-dependencies from dependencies."""

    PLUGIN_NAME = "min_requirements"

    def update(self, metadata: dict) -> None:
        """Update the project.optional-dependencies metadata."""
        breakpoint()


@hookimpl
def hatch_register_metadata_hook() -> type[MetadataHookInterface]:
    return MinRequirementsMetadataHook


def minimize_requirement(requirement: str) -> str:
    try:
        # we specifically use name_req() instead of specification() here
        # to exclude url_req
        name, extras, constraints, _ = parse_name_req(requirement)
    except ParseError:
        # If the requirement is not a name_req, return it unchanged
        return requirement
    if not (min_version := min_allowable_version(constraints)):
        return requirement
    markers = requirement.split(";", 1)[1] if ";" in requirement else ""
    return serialize_name_req(name, extras, [min_version], markers)


def serialize_name_req(
    name: str, extras: list[str], constraints: list[VersionOne], markers: str
) -> str:
    """Put all the parts of a name_req back together into a single string."""
    out = name
    if extras:
        out += f"[{','.join(extras)}]"
    if constraints:
        out += ",".join(f"{op}{v}" for op, v in constraints)
    if markers:
        out += " ;" + markers
    return out


def min_allowable_version(constraints: list[VersionOne]) -> VersionOne | None:
    """Given a list of version constraints, return the minimum allowable version.

    Examples
    --------
    >>> get_min_constraint([(">=", "1"), ("<", "2")])
    ("==", "1")
    >>> get_min_constraint([(">", "1"), ("<", "2")])
    ("==", "1")
    >>> get_min_constraint([("~=", "1.2.3")])
    ("==", "1.2.3")
    >>> get_min_constraint([("==", "1.2.3")])
    ("==", "1.2.3")
    """
    if not constraints:
        return None
    if len(constraints) == 1:
        return ("==", constraints[0][-1])

    # FIXME: this is not correct
    min_version = constraints[0][1]
    for _op, version in constraints[1:]:
        if version < min_version:
            min_version = version
    return ("==", min_version)


def parse_name_req(requirement: str) -> tuple[str, list[str], list[VersionOne], str | None]:
    """Parse a PEP 508 requirement string into name, extras, constraints, and marker.

    we specifically use `name_req()` instead of `specification()` here
    and allow url_req to raise a ParseError
    """
    grammar = _compiled_grammar()
    try:
        # fail if it's not a valid requirement at all
        grammar(requirement).specification()
    except ParseError as e:
        raise ValueError(f"Invalid requirement: {requirement}") from e

    # then ensure it is a name_req
    return grammar(requirement).name_req()  # type: ignore


_COMPILED_GRAMMAR: Callable[[str], _GrammarWrapper] | None = None


def _compiled_grammar() -> Callable[[str], _GrammarWrapper]:
    global _COMPILED_GRAMMAR
    if _COMPILED_GRAMMAR is None:
        _COMPILED_GRAMMAR = makeGrammar(_GRAMMAR, {"lookup": lambda name: name})
    return _COMPILED_GRAMMAR


# grammar for parsing requirements from PEP 508 strings
# https://packaging.python.org/en/latest/specifications/dependency-specifiers/
# with '\\'' replaced by "'"
_GRAMMAR = r"""
wsp           = ' ' | '\t'
version_cmp   = wsp* <'<=' | '<' | '!=' | '==' | '>=' | '>' | '~=' | '==='>
version       = wsp* <( letterOrDigit | '-' | '_' | '.' | '*' | '+' | '!' )+>
version_one   = version_cmp:op version:v wsp* -> (op, v)
version_many  = version_one:v1 (wsp* ',' version_one)*:v2 -> [v1] + v2
versionspec   = ('(' version_many:v ')' ->v) | version_many
urlspec       = '@' wsp* <URI_reference>
marker_op     = version_cmp | (wsp* 'in') | (wsp* 'not' wsp+ 'in')
python_str_c  = (wsp | letter | digit | '(' | ')' | '.' | '{' | '}' |
                 '-' | '_' | '*' | '#' | ':' | ';' | ',' | '/' | '?' |
                 '[' | ']' | '!' | '~' | '`' | '@' | '$' | '%' | '^' |
                 '&' | '=' | '+' | '|' | '<' | '>' )
dquote        = '"'
squote        = "'"
python_str    = (squote <(python_str_c | dquote)*>:s squote |
                 dquote <(python_str_c | squote)*>:s dquote) -> s
env_var       = ('python_version' | 'python_full_version' |
                 'os_name' | 'sys_platform' | 'platform_release' |
                 'platform_system' | 'platform_version' |
                 'platform_machine' | 'platform_python_implementation' |
                 'implementation_name' | 'implementation_version' |
                 'extra' # ONLY when defined by a containing layer
                 ):varname -> lookup(varname)
marker_var    = wsp* (env_var | python_str)
marker_expr   = marker_var:l marker_op:o marker_var:r -> (o, l, r)
              | wsp* '(' marker:m wsp* ')' -> m
marker_and    = marker_expr:l wsp* 'and' marker_expr:r -> ('and', l, r)
              | marker_expr:m -> m
marker_or     = marker_and:l wsp* 'or' marker_and:r -> ('or', l, r)
                  | marker_and:m -> m
marker        = marker_or
quoted_marker = ';' wsp* marker
identifier_end = letterOrDigit | (('-' | '_' | '.' )* letterOrDigit)
identifier    = < letterOrDigit identifier_end* >
name          = identifier
extras_list   = identifier:i (wsp* ',' wsp* identifier)*:ids -> [i] + ids
extras        = '[' wsp* extras_list?:e wsp* ']' -> e
name_req      = (name:n wsp* extras?:e wsp* versionspec?:v wsp* quoted_marker?:m
                 -> (n, e or [], v or [], m))
url_req       = (name:n wsp* extras?:e wsp* urlspec:v (wsp+ | end) quoted_marker?:m
                 -> (n, e or [], v, m))
specification = wsp* ( url_req | name_req ):s wsp* -> s
# The result is a tuple - name, list-of-extras,
# list-of-version-constraints-or-a-url, marker-ast or None


URI_reference = <URI | relative_ref>
URI           = scheme ':' hier_part ('?' query )? ( '#' fragment)?
hier_part     = ('//' authority path_abempty) | path_absolute | path_rootless | path_empty
absolute_URI  = scheme ':' hier_part ( '?' query )?
relative_ref  = relative_part ( '?' query )? ( '#' fragment )?
relative_part = '//' authority path_abempty | path_absolute | path_noscheme | path_empty
scheme        = letter ( letter | digit | '+' | '-' | '.')*
authority     = ( userinfo '@' )? host ( ':' port )?
userinfo      = ( unreserved | pct_encoded | sub_delims | ':')*
host          = IP_literal | IPv4address | reg_name
port          = digit*
IP_literal    = '[' ( IPv6address | IPvFuture) ']'
IPvFuture     = 'v' hexdig+ '.' ( unreserved | sub_delims | ':')+
IPv6address   = (
                  ( h16 ':'){6} ls32
                  | '::' ( h16 ':'){5} ls32
                  | ( h16 )?  '::' ( h16 ':'){4} ls32
                  | ( ( h16 ':')? h16 )? '::' ( h16 ':'){3} ls32
                  | ( ( h16 ':'){0,2} h16 )? '::' ( h16 ':'){2} ls32
                  | ( ( h16 ':'){0,3} h16 )? '::' h16 ':' ls32
                  | ( ( h16 ':'){0,4} h16 )? '::' ls32
                  | ( ( h16 ':'){0,5} h16 )? '::' h16
                  | ( ( h16 ':'){0,6} h16 )? '::' )
h16           = hexdig{1,4}
ls32          = ( h16 ':' h16) | IPv4address
IPv4address   = dec_octet '.' dec_octet '.' dec_octet '.' dec_octet
nz            = ~'0' digit
dec_octet     = (
                  digit # 0-9
                  | nz digit # 10-99
                  | '1' digit{2} # 100-199
                  | '2' ('0' | '1' | '2' | '3' | '4') digit # 200-249
                  | '25' ('0' | '1' | '2' | '3' | '4' | '5') )# %250-255
reg_name = ( unreserved | pct_encoded | sub_delims)*
path = (
        path_abempty # begins with '/' or is empty
        | path_absolute # begins with '/' but not '//'
        | path_noscheme # begins with a non-colon segment
        | path_rootless # begins with a segment
        | path_empty ) # zero characters
path_abempty  = ( '/' segment)*
path_absolute = '/' ( segment_nz ( '/' segment)* )?
path_noscheme = segment_nz_nc ( '/' segment)*
path_rootless = segment_nz ( '/' segment)*
path_empty    = pchar{0}
segment       = pchar*
segment_nz    = pchar+
segment_nz_nc = ( unreserved | pct_encoded | sub_delims | '@')+
                # non-zero-length segment without any colon ':'
pchar         = unreserved | pct_encoded | sub_delims | ':' | '@'
query         = ( pchar | '/' | '?')*
fragment      = ( pchar | '/' | '?')*
pct_encoded   = '%' hexdig
unreserved    = letter | digit | '-' | '.' | '_' | '~'
reserved      = gen_delims | sub_delims
gen_delims    = ':' | '/' | '?' | '#' | '(' | ')?' | '@'
sub_delims    = '!' | '$' | '&' | "'" | '(' | ')' | '*' | '+' | ',' | ';' | '='
hexdig        = digit | 'a' | 'A' | 'b' | 'B' | 'c' | 'C' | 'd' | 'D' | 'e' | 'E' | 'f' | 'F'
"""
