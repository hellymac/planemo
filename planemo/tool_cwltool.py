
import pprint
import argparse
import functools
import io
import logging
import os
import signal
import sys
import time
import urllib
from codecs import StreamWriter, getwriter
from collections.abc import MutableMapping, MutableSequence
from typing import (
    IO,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sized,
    TextIO,
    Tuple,
    Union,
    cast,
)

import coloredlogs
import pkg_resources  # part of setuptools
from ruamel import yaml
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from schema_salad.exceptions import ValidationException
from schema_salad.ref_resolver import (
    ContextType,
    FetcherCallableType,
    Loader,
    file_uri,
    uri_file_path,
)
from schema_salad.sourceline import strip_dup_lineno
from schema_salad.utils import json_dumps

from cwltool import main
from cwltool import command_line_tool, workflow
from cwltool.argparser import arg_parser, generate_parser, get_default_args
from cwltool.builder import HasReqsHints
from cwltool.context import LoadingContext, RuntimeContext, getdefault
from cwltool.cwlrdf import printdot, printrdf
from cwltool.errors import UnsupportedRequirement, WorkflowException
from cwltool.executors import JobExecutor, MultithreadedJobExecutor, SingleJobExecutor
from cwltool.load_tool import (
    default_loader,
    fetch_document,
    jobloaderctx,
    load_overrides,
    make_tool,
    resolve_and_validate_document,
    resolve_overrides,
    resolve_tool_uri,
)
from cwltool.loghandler import _logger, defaultStreamHandler
from cwltool.mutation import MutationManager
from cwltool.pack import pack
from cwltool.process import (
    CWL_IANA,
    Process,
    add_sizes,
    scandeps,
    shortname,
    use_custom_schema,
    use_standard_schema,
)
from cwltool.procgenerator import ProcessGenerator
from cwltool.provenance import ResearchObject
from cwltool.resolver import ga4gh_tool_registries, tool_resolver
from cwltool.secrets import SecretStore
from cwltool.software_requirements import (
    DependenciesConfiguration,
    get_container_from_software_requirements,
)
from cwltool.stdfsaccess import StdFsAccess
from cwltool.subgraph import get_subgraph
from cwltool.update import ALLUPDATES, UPDATES
from cwltool.utils import (
    DEFAULT_TMP_PREFIX,
    CWLObjectType,
    CWLOutputAtomType,
    CWLOutputType,
    adjustDirObjs,
    normalizeFilesDirs,
    onWindows,
    processes_to_kill,
    trim_listing,
    versionstring,
    visit_class,
    windows_default_container_id,
)
from cwltool.workflow import Workflow
from cwltool.mpi import MpiConfig
import logging

_logger = logging.getLogger("cwltool")  # pylint: disable=invalid-name
defaultStreamHandler = logging.StreamHandler()  # pylint: disable=invalid-name
_logger.addHandler(defaultStreamHandler)
_logger.setLevel(logging.INFO)

def get_tool(ctx, filename):
    stderr = sys.stderr
    runtimeContext = RuntimeContext(vars(ctx))
    for key, val in get_default_args().items():
        if not hasattr(ctx, key):
            setattr(ctx, key, val)
    
    _logger.removeHandler(defaultStreamHandler)
    stderr_handler = None

    if stderr_handler is not None:
        _logger.addHandler(stderr_handler)
    else:
        coloredlogs.install(logger=_logger, stream=stderr)
        print(_logger.handlers)
        stderr_handler = _logger.handlers[-1]
    main.configure_logging(ctx, stderr_handler, runtimeContext)
    loadingContext = None
    loadingContext = main.setup_loadingContext(loadingContext, runtimeContext, ctx)
    uri, tool_file_uri = resolve_tool_uri(
        filename,
        resolver=loadingContext.resolver,
        fetcher_constructor=loadingContext.fetcher_constructor,
        ) 
    loadingContext, workflowobj, uri = fetch_document(uri, loadingContext)

    loadingContext, uri = resolve_and_validate_document(
                loadingContext,
                workflowobj,
                uri,
                preprocess_only=(ctx.print_pre or ctx.pack),
                skip_schemas=ctx.skip_schemas,
            )
    
    if loadingContext.loader is None:
        raise Exception("Impossible code path.")
    processobj, metadata = loadingContext.loader.resolve_ref(uri)
    processobj = cast(CommentedMap, processobj)  


    # print(runtimeContext)
    return main.make_tool(uri,loadingContext)