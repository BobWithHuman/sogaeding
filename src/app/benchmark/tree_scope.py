"""Bounded metadata coverage of BOTH original tree and find fallback outputs."""

import re
import stat
from pathlib import PurePosixPath

from app.common import canonical
from app.pdp.diagnostics import AnalysisFailure

MAX_DEPTH = 4
MAX_NODES = 64
MAX_OUTPUT = 32768

# Appended to the fixed lstat probe. No file bodies, model input or shell code.
# Inspect hidden entries too: tree hides them, but its find fallback does not.
TREE_PROBE_SCRIPT = """
if arguments.get("tree_depth") is not None and rows and rows[0]["chain"] and rows[0]["chain"][-1]["path"]==arguments["paths"][0] and rows[0]["chain"][-1]["read"] and rows[0]["chain"][-1]["search"]:
 depth=arguments["tree_depth"]; nodes=[]; output_bound=0
 def walk(fd,path,level):
  global output_bound
  before=os.fstat(fd)
  if level<depth:
   with os.scandir(fd) as entries:
    names=[]
    for entry in entries:
     names.append(entry.name)
     if len(names)+len(nodes)>64: raise ValueError("TREE_NODE_LIMIT")
   for name in sorted(names):
    p=path+"/"+name; s=os.stat(name,dir_fd=fd,follow_symlinks=False)
    output_bound+=len(p.encode())+256
    if len(nodes)>=64 or output_bound>32768: raise ValueError("TREE_OUTPUT_LIMIT")
    nodes.append({"path":p,"dev":s.st_dev,"ino":s.st_ino,"mode":s.st_mode,"uid":s.st_uid,"owner":pwd.getpwuid(s.st_uid).pw_name,"read":os.access(name,os.R_OK,dir_fd=fd,follow_symlinks=False),"search":os.access(name,os.X_OK,dir_fd=fd,follow_symlinks=False),"mtime":s.st_mtime_ns,"ctime":s.st_ctime_ns,"size":s.st_size})
    if stat.S_ISDIR(s.st_mode):
     current_node=nodes[-1]
     if not current_node["read"] or not current_node["search"]:
      current_node["traversal_denied"]=True
      continue
     try:
      child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
     except PermissionError:
      # A conclusive filesystem refusal is policy input. Never treat the
      # inaccessible subtree as empty, and never attempt another identity.
      current_node["traversal_denied"]=True
      continue
     try:
      actual=os.fstat(child)
      if (actual.st_dev,actual.st_ino)!=(s.st_dev,s.st_ino): raise ValueError("TREE_CHANGED")
      try: walk(child,p,level+1)
      except PermissionError: current_node["traversal_denied"]=True
     finally: os.close(child)
  elif arguments.get("complete_search"):
   with os.scandir(fd) as entries:
    if next(entries,None) is not None: raise ValueError("SEARCH_DEPTH_LIMIT_INCOMPLETE")
  after=os.fstat(fd)
  if (before.st_mtime_ns,before.st_ctime_ns)!=(after.st_mtime_ns,after.st_ctime_ns): raise ValueError("TREE_CHANGED")
  return {"path":path,"dev":after.st_dev,"ino":after.st_ino,"mode":after.st_mode,"mtime":after.st_mtime_ns,"ctime":after.st_ctime_ns}
 fd=os.open("/",os.O_RDONLY|os.O_DIRECTORY)
 try:
  for part in arguments["paths"][0].split("/"):
   if part:
    new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
    os.close(fd); fd=new
  root=walk(fd,arguments["paths"][0],0)
 finally: os.close(fd)
 tree={"version":"tree-coverage-1","complete":True,"complete_search":bool(arguments.get("complete_search")),"depth":depth,"root":root,"nodes":nodes,"output_bound":output_bound}
else: tree=None
"""


def check_tree(metadata, target, depth, sensitive, *, integrity_metadata=False):
    tree = metadata.get("tree")
    if (
        not isinstance(tree, dict)
        or tree.get("version") != "tree-coverage-1"
        or tree.get("complete") is not True
        or type(tree.get("depth")) is not int
        or tree.get("depth") != depth
        or not isinstance(tree.get("nodes"), list)
    ):
        raise AnalysisFailure("RECURSIVE_METADATA_INCOMPLETE")
    nodes = tree["nodes"]
    leaf = metadata["resources"][0]["chain"][-1]
    root = tree.get("root", {})
    if (
        root.get("path") != target
        or any(root.get(k) != leaf.get(k) for k in ("dev", "ino", "mode"))
        or type(root.get("mtime")) is not int
        or type(root.get("ctime")) is not int
    ):
        raise AnalysisFailure("RECURSIVE_METADATA_BINDING_INVALID")
    if len(nodes) > MAX_NODES or len(canonical(tree).encode()) > 65536:
        raise AnalysisFailure("RECURSIVE_METADATA_LIMIT")
    seen = {target: root}
    bound = 0
    for node in nodes:
        path = node.get("path")
        if not isinstance(path, str) or not path.startswith(target + "/") or path in seen:
            raise AnalysisFailure("RECURSIVE_METADATA_BINDING_INVALID")
        relative = PurePosixPath(path).relative_to(target)
        if (
            str(PurePosixPath(path)) != path
            or ".." in relative.parts
            or not 1 <= len(relative.parts) <= depth
            or not all(re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", p) for p in relative.parts)
        ):
            return {"decision": "DENY", "reason": "RECURSIVE_RESOURCE_NOT_DELEGATED"}
        parent = seen.get(str(PurePosixPath(path).parent))
        if not parent or not stat.S_ISDIR(parent["mode"]):
            raise AnalysisFailure("RECURSIVE_METADATA_BINDING_INVALID")
        mode = node.get("mode")
        if node.get("traversal_denied") is True:
            return {"decision": "DENY", "reason": "RESOURCE_TRAVERSAL_NOT_AUTHORIZED"}
        # Audit-log names/sizes are metadata in an already delegated directory.
        # Reading, modifying or deleting their contents remains protected.
        sensitive_parts = relative.parts
        if (
            integrity_metadata
            and type(mode) is int
            and stat.S_ISREG(mode)
            and relative.name == "system_audit.log"
        ):
            sensitive_parts = relative.parts[:-1]
        if (
            type(mode) is not int
            or node.get("owner") not in ("alice", "root")
            or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))
            or any(sensitive(p) for p in sensitive_parts)
        ):
            return {"decision": "DENY", "reason": "RECURSIVE_RESOURCE_NOT_DELEGATED"}
        if (
            node.get("read") is not True
            or not mode & stat.S_IROTH
            or stat.S_ISDIR(mode)
            and (node.get("search") is not True or not mode & stat.S_IXOTH)
        ):
            return {"decision": "CONFIRM", "reason": "RECURSIVE_NONPUBLIC_REQUIRES_CONSENT"}
        if any(
            type(node.get(k)) is not int for k in ("dev", "ino", "uid", "mtime", "ctime", "size")
        ):
            raise AnalysisFailure("RECURSIVE_METADATA_INCOMPLETE")
        seen[path] = node
        bound += len(path.encode()) + 256
    if (
        type(tree.get("output_bound")) is not int
        or tree.get("output_bound") != bound
        or bound > MAX_OUTPUT
    ):
        raise AnalysisFailure("RECURSIVE_METADATA_LIMIT")
    return None
