"""MAIN / RECOMMENDED method: export from the LIVE Viber connection.

Makes Viber's own (already-unlocked) SQLCipher engine copy the decrypted tables into an
UNENCRYPTED file via  ATTACH DATABASE ... KEY ''  +  CREATE TABLE AS SELECT.
Uses ONLY QSqlQuery::exec (bool) - no QVariant/value iteration (that used to freeze/crash
Viber). Runs on the 'viber.db' connection, and only once it catches a SELECT on a viber
table (meaning: correct thread + autocommit, so ATTACH does not fail).

Requires: Viber Desktop running and logged in.
"""
import os, time, json, sqlite3
import frida
from . import config
from .frida_common import require_viber

TABLES = ["Contact", "Messages", "Events", "ChatInfo", "ChatRelation"]

JS = r"""
var PLAIN = %%PLAIN%%;
var TABLES = %%TABLES%%;

// Cross-platform Qt module lookup.
//   Windows : Qt6Sql.dll / Qt6Core.dll (MSVC-mangled exports)
//   Linux   : libQt6Sql.so.6 / libQt5Core.so.5 ... (Itanium-mangled exports)
//   macOS   : QtSql / QtCore frameworks (Itanium-mangled exports)
function findQtModule(kind){
  var mods=Process.enumerateModules(), re=new RegExp('qt\\d?'+kind,'i');
  for(var i=0;i<mods.length;i++){ if(re.test(mods[i].name.replace(/[^a-z0-9]/gi,''))) return mods[i]; }
  return null;
}
function expMapMod(m){var o={};if(!m)return o;try{m.enumerateExports().forEach(function(e){o[e.name]=e.address;});}catch(e){}return o;}
var modSql=findQtModule('sql'), modCore=findQtModule('core');
var S=expMapMod(modSql), C=expMapMod(modCore);
// pick: try a list of name fragments. Each needed symbol lists BOTH the MSVC
// fragment (Windows) and the Itanium fragment (Linux/macOS), so one lookup works
// on every platform without changing the hooking logic below.
function pick(map,subs){if(typeof subs==='string')subs=[subs];for(var k in map){for(var j=0;j<subs.length;j++){if(k.indexOf(subs[j])>=0)return map[k];}}return null;}
function need(addr,label){if(!addr){send({t:'err',msg:'symbol not found: '+label+' (Sql module='+(modSql?modSql.name:'MISSING')+', Core module='+(modCore?modCore.name:'MISSING')+'). Unsupported Viber/Qt build?'});throw new Error('missing symbol: '+label);}return addr;}

var EXEC=['exec@QSqlQuery@@QEAA_NAEBVQString','9QSqlQuery4execERK7QString'];
var f_database=new NativeFunction(need(pick(S,['database@QSqlDatabase','12QSqlDatabase8databaseE']),'QSqlDatabase::database'),'void',['pointer','pointer','bool']);
var f_ctorQ   =new NativeFunction(need(pick(S,['0QSqlQuery@@QEAA@AEBVQSqlDatabase','9QSqlQueryC1ERK12QSqlDatabase','9QSqlQueryC2ERK12QSqlDatabase']),'QSqlQuery(QSqlDatabase)'),'void',['pointer','pointer']);
var f_exec    =new NativeFunction(need(pick(S,EXEC),'QSqlQuery::exec(QString)'),'bool',['pointer','pointer']);
var f_dtorQ   =new NativeFunction(need(pick(S,['1QSqlQuery@@QEAA@XZ','9QSqlQueryD1Ev','9QSqlQueryD2Ev']),'~QSqlQuery'),'void',['pointer']);
var f_dtorDb  =new NativeFunction(need(pick(S,['1QSqlDatabase@@QEAA@XZ','12QSqlDatabaseD1Ev','12QSqlDatabaseD2Ev']),'~QSqlDatabase'),'void',['pointer']);
var a_prep    =pick(S,['prepare@QSqlQuery','9QSqlQuery7prepareE']);
var a_exec    =pick(S,EXEC);

var a_fromU16 =pick(C,['fromUtf16@QString@@SA?AV1@PEB_S','fromUtf16@QString','7QString8fromUtf16E']);
var f_fromU16 =new NativeFunction(need(a_fromU16,'QString::fromUtf16'),'void',['pointer','pointer','int64']);
var f_dtorStr =new NativeFunction(need(pick(C,['1QString@@QEAA@XZ','7QStringD1Ev','7QStringD2Ev']),'~QString'),'void',['pointer']);

function readQString(p){try{var d=p.add(8).readPointer();var s=p.add(16).readLong();if(d.isNull()||s<=0||s>1e6)return "";return d.readUtf16String(s);}catch(e){return "";}}
function makeQString(s){var buf=Memory.alloc(32);var u=Memory.allocUtf16String(s);f_fromU16(buf,u,s.length);return buf;}

var VIBER_RE=/Events|Messages|Contact|ChatInfo|ChatRelation/i;
var done=false, busy=false;
var listeners=[];

function run(q, sql){
  var qs=makeQString(sql);
  var ok=false;
  try{ ok=f_exec(q, qs); }catch(e){ send({t:'log', m:'EXC '+sql.slice(0,40)+' :: '+e}); }
  try{ f_dtorStr(qs); }catch(e){}
  return ok?1:0;
}

function harvest(conn){
  var connQ=makeQString(conn);
  var db=Memory.alloc(16); f_database(db,connQ,1);
  var q=Memory.alloc(16);  f_ctorQ(q,db);
  var r={};
  r.attach = run(q, "ATTACH DATABASE '"+PLAIN+"' AS vplain KEY ''");
  if(r.attach){
    r.tables={};
    for(var i=0;i<TABLES.length;i++){
      var t=TABLES[i];
      r.tables[t]=run(q, "CREATE TABLE vplain."+t+" AS SELECT * FROM "+t);
    }
    r.detach = run(q, "DETACH DATABASE vplain");
  }
  try{ f_dtorQ(q); }catch(e){}
  try{ f_dtorDb(db); }catch(e){}
  var ok = r.attach && r.tables && r.tables['Contact'];
  send({t:'result', r:r, ok:ok?1:0});
  return ok;
}

function onSql(){
  return function(){
    if(done||busy) return;
    if(!this.sql || !/select/i.test(this.sql) || !VIBER_RE.test(this.sql)) return;
    busy=true;
    try{
      if(harvest('viber.db')){ done=true; listeners.forEach(function(x){try{x.detach();}catch(e){}}); send({t:'done'}); }
    }catch(e){ send({t:'err', msg:''+e+'\n'+(e.stack||'')}); }
    busy=false;
  };
}
function arm(addr){ if(!addr)return; var L=Interceptor.attach(addr,{onEnter:function(a){this.sql=readQString(a[1]);},onLeave:onSql()}); listeners.push(L); }
arm(a_exec); arm(a_prep);
send({t:'armed', hooks:listeners.length});
"""


def run(timeout=90):
    pid = require_viber()
    print(f"[i] Viber pid={pid}")
    out = config.export_db_path()
    tmp = out + ".new"                      # write to a temp file; the original is kept until success
    for ext in ("", "-wal", "-shm", "-journal"):
        if os.path.exists(tmp + ext):
            os.remove(tmp + ext)

    js = (JS.replace("%%PLAIN%%", json.dumps(tmp.replace("\\", "/")))
            .replace("%%TABLES%%", json.dumps(TABLES)))

    state = {"done": False}

    def on_msg(m, d):
        if m.get("type") == "send":
            p = m["payload"]; t = p.get("t")
            if t == "armed":
                print(f"[i] hooks: {p.get('hooks')} - if nothing happens in a few sec, click a chat in Viber")
            elif t == "log":
                print("   [js]", p.get("m"))
            elif t == "result":
                print(f"[i] result: ok={p.get('ok')}  {p.get('r')}")
            elif t == "err":
                print("[JS ERR]", p.get("msg")); state["done"] = True
            elif t == "done":
                state["done"] = True
        elif m.get("type") == "error":
            print("[ERR]", m.get("stack")); state["done"] = True

    s = frida.attach(pid)
    sc = s.create_script(js)
    sc.on("message", on_msg)
    sc.load()
    print(f"[i] waiting for a SELECT on viber.db (up to {timeout}s)...")
    t0 = time.time()
    while not state["done"] and time.time() - t0 < timeout:
        time.sleep(0.2)
    s.detach()

    if not os.path.exists(tmp):
        print("\n[X] Export not created. There was probably no activity on viber.db - "
              "open a chat and run again. (The previous export is preserved.)")
        return False

    os.replace(tmp, out)                     # success -> replace the original
    for ext in ("-wal", "-shm", "-journal"):
        if os.path.exists(tmp + ext):
            os.remove(tmp + ext)
    print(f"\n[i] export: {out}  ({os.path.getsize(out)} B)")
    con = sqlite3.connect(out); c = con.cursor()
    for t in TABLES:
        try:
            c.execute(f"SELECT count(*) FROM {t}")
            print(f"    {t}: {c.fetchone()[0]} rows")
        except Exception as e:
            print(f"    {t}: missing ({e})")
    con.close()
    return True
