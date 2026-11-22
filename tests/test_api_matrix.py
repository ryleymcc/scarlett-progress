"""Source symbol grid regression tests. No upstream requests required."""
import base64
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import api_matrix as matrix


class SourceParseTests(unittest.TestCase):
    def test_cpp_definitions_stubs_and_references(self):
        source = """
// HRESULT XUserGetName() { return S_OK; }  comment only
HRESULT XUserGetId(int user) {
    return S_OK;
}
HRESULT XMemAlloc(int size) {
    return E_NOTIMPL;
}
void call_game(void) {
    XGameSaveCreate("test");
}
"""
        found = matrix.source_symbols(source, "src/shims/gdk.cpp", "owner/project", "main")
        self.assertEqual(found["XUserGetId"]["status"], "definition_candidate")
        self.assertEqual(found["XMemAlloc"]["status"], "stub_candidate")
        self.assertEqual(found["XGameSaveCreate"]["status"], "reference")
        self.assertNotIn("XUserGetName", found)
        self.assertIn("github.com/owner/project/blob/main/src/shims/gdk.cpp#L", found["XUserGetId"]["source"])

    def test_rust_and_python_bodies(self):
        rust = """pub unsafe extern "C" fn XGameSaveSubmitUpdate(a: u32) -> i32 { 0 }"""
        py = """def XTaskQueueDispatch(self, a):
    return 1
"""
        self.assertEqual(
            matrix.source_symbols(rust, "src/lib.rs", "test/rust", "main")["XGameSaveSubmitUpdate"]["status"],
            "definition_candidate"
        )
        self.assertEqual(
            matrix.source_symbols(py, "runtime/x_task.py", "test/python", "main")["XTaskQueueDispatch"]["status"],
            "definition_candidate"
        )

    def test_prototype_is_not_a_definition(self):
        source = "extern HRESULT XUserGetId(int index);"
        self.assertEqual(matrix.source_symbols(source, "src/xuser.h", "a/b", "main")["XUserGetId"]["status"], "reference")

    def test_vendored_generated_docs_are_excluded(self):
        for path in ("third_party/lib/xuser.cpp", "docs/xuser.cpp", "tests/xuser.cpp", "build/xuser.cpp"):
            self.assertFalse(matrix.is_source({"type":"blob","path":path,"size":123}))
        self.assertTrue(matrix.is_source({"type":"blob","path":"src/shims/xuser.cpp","size":2000}))
        self.assertFalse(matrix.is_source({"type":"blob","path":"src/shims/xuser.cpp","size":999_999}))

    def test_missing_source_is_unknown_not_absent(self):
        result = matrix.build_matrix([
            {"repo":"a/one","name":"One","api_scan":{"status":"partial","symbols":{
                "XUserGetId":{"status":"definition_candidate","source":"https://github.com/a/one/blob/main/a.cpp#L1"}}}},
            {"repo":"b/two","name":"Two","api_scan":{"status":"error","symbols":{}}},
        ])
        self.assertEqual(result["repositories_scanned"], 1)
        self.assertEqual(result["rows"][0]["project_count"], 1)
        self.assertNotIn("b/two", result["rows"][0]["sources"])


class CollectionTests(unittest.TestCase):
    def test_bounded_scan(self):
        src1 = b"HRESULT XUserGetId(int a) { return 0; }"
        src2 = b"HRESULT XUserGetId(int a) { return E_NOTIMPL; } XMemAlloc(10);"
        docs = {"src/shims/user.cpp":src1, "src/shims/other.cpp":src2}
        def api_get(path, params=None, missing_ok=False):
            if "/git/trees/" in path:
                return {"truncated":False, "tree":[
                    {"type":"blob","path":p,"size":len(src)}
                    for p,src in docs.items()
                ]}, ""
            if "/contents/" in path:
                from urllib.parse import unquote
                found=docs[unquote(path.split("/contents/",1)[1])]
                return {"encoding":"base64","content":base64.b64encode(found).decode("ascii")}, ""
            raise AssertionError(path)
        scan=matrix.scan_repository("demo/repo","main",api_get)
        self.assertEqual(scan["status"],"ok")
        self.assertEqual(scan["files_scanned"],2)
        self.assertEqual(scan["symbols"]["XUserGetId"]["status"],"definition_candidate")
        self.assertEqual(scan["symbols"]["XMemAlloc"]["status"],"reference")
        self.assertEqual(matrix.group_name("XMemAlloc"), "Memory")

    def test_shared_symbol_union_has_source_links(self):
        finding=lambda s:{"status":s,"source":"https://github.com/x/y/blob/main/file.cpp#L4"}
        projects=[
            {"name":"One","repo":"demo/one","api_scan":{"status":"ok","symbols":{"XGameSaveCreate":finding("reference")}}},
            {"name":"Two","repo":"demo/two","api_scan":{"status":"partial","symbols":{"XGameSaveCreate":finding("definition_candidate"),"XMemAlloc":finding("stub_candidate")}}},
        ]
        result=matrix.build_matrix(projects)
        shared=next(r for r in result["rows"] if r["symbol"]=="XGameSaveCreate")
        self.assertEqual(shared["project_count"],2)
        self.assertEqual(shared["candidate_count"],1)
        self.assertEqual(shared["group"],"Saved data")
        self.assertEqual(len(shared["sources"]),2)


if __name__ == "__main__":
    unittest.main()
