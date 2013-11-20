from tempfile import NamedTemporaryFile
import json
import os
import sys
import posixpath
import BaseHTTPServer
import urllib
import cgi
import shutil
import mimetypes
from StringIO import StringIO
import subprocess

slicer_executable = "Slic3r_gnulinux/bin/slic3r"
printer_path = "profiles/printer"
print_path = "profiles/print"
filament_path = "profiles/filament"

support_material = False #TODO: let the user decide
fill_density = 0.2 #TODO: let the user decide
printer_profile = "Metamaquina2" #TODO: let the user decide
print_profile = "Padrao" #TODO: let the user decide
filament_profile = "ABS" #TODO: let the user decide

#TODO: update these values based on messages received from the firmware of the 3d printer
bed_temperature = 0
extruder_temperature = 0

recvcb = None
def received_msg_from_fw(msg):
  global extruder_temperature, bed_temperature

# example of a typical temperature message:
# "T:239.49 B:89.65 @:94"
  try:
    extruder_temperature = msg.split("T:")[1].split(" ")[0]
    bed_temperature = msg.split("B:")[1].split(" ")[0]
  except:
    pass

  if recvcb:
    recvcb(msg)

def executa_fatiamento(slicecommand):
  import shlex
  param = slicecommand
  print "Fatiando: ", param
  pararray = [i for i in shlex.split(param)]
  print pararray
  processo_de_fatiamento = subprocess.Popen(pararray, stdin = subprocess.PIPE, stderr = subprocess.STDOUT, stdout = subprocess.PIPE)
  while True:
    o = processo_de_fatiamento.stdout.read(1)
    if o == '' and processo_de_fatiamento.poll() != None: break
    sys.stdout.write(o)
  processo_de_fatiamento.wait()

if support_material:
  support_material_param = "--support_material"
else:
  support_material_param = ""

def invoke_3d_print_job(path):
  print "We will print this file:", path
  input_file = path
  output_file = path + ".gcode" #TODO: generate it based on input filename

  slicecommand = "%s --load %s/%s.ini --load %s/%s.ini --load %s/%s.ini --fill-density %s %s %s --output %s" % (slicer_executable, printer_path, printer_profile, print_path, print_profile, filament_path, filament_profile, str(fill_density), support_material_param, input_file, output_file)
  print "We'll slice it with the following command: ", slicecommand
  executa_fatiamento(slicecommand)

  gcode = [i.replace("\n", "") for i in open(output_file)]
  core.startprint(gcode)

__version__ = "0.6"

#these are ugly hacks. Please investigate.
get_counter = 0
post_counter = 0

class TreeDeePrinterRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    """Simple HTTP request handler with GET and HEAD commands.

    This serves files from the current directory and any of its
    subdirectories.  It assumes that all files are plain text files
    unless they have the extension ".html" in which case it assumes
    they are HTML files.

    The GET and HEAD requests are identical except that the HEAD
    request omits the actual contents of the file.

    """

    server_version = "SimpleHTTP/" + __version__

    def do_POST(self):
        global post_counter
        post_counter+=1
        if post_counter%2:
          form = cgi.FieldStorage(
              fp=self.rfile,
              headers=self.headers,
              environ={'REQUEST_METHOD':'POST',
                       'CONTENT_TYPE':self.headers['Content-Type'],
                       })

          tempfile = NamedTemporaryFile( suffix=".stl", prefix="tmp_", delete=False )
          tempfile.write(form['file'].value)
          tempfile.close()
          invoke_3d_print_job(tempfile.name)

    def do_GET(self):
        """Serve a GET request."""
        global get_counter
        get_counter+=1

        if self.path.startswith("/oldprint"):
          if get_counter%2:
            invoke_3d_print_job(self.path.split("/oldprint")[1])
        elif self.path.startswith("/status.json"):
          status = {"bed": bed_temperature,\
                    "extruder": extruder_temperature}

          self.send_response(200)
          self.send_header("Content-type", "application/json")
          self.end_headers()
          self.wfile.write(json.dumps(status))
        else:
          f = self.send_head()
          if f:
              self.copyfile(f, self.wfile)
              f.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)

        f = None
        if os.path.isdir(path):
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        if ctype.startswith('text/'):
            mode = 'r'
        else:
            mode = 'rb'
        try:
            f = open(path, mode)
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.end_headers()
        return f

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(lambda a, b: cmp(a.lower(), b.lower()))
        f = StringIO()
        f.write("<title>Directory listing for %s</title>\n" % self.path)
        f.write("<h2>Directory listing for %s</h2>\n" % self.path)
        f.write("<hr>\n<ul>\n")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name = cgi.escape(name)
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write('<li><a href="%s">%s</a>\n' % (linkname, displayname))
        f.write("</ul>\n<hr>\n")
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        return f

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path

    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile)

    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using text/plain
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """

        base, ext = posixpath.splitext(path)
        if self.extensions_map.has_key(ext):
            return self.extensions_map[ext]
        ext = ext.lower()
        if self.extensions_map.has_key(ext):
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream', # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        })


serial_port = '/dev/ttyACM0'
baud_rate = 115200

from printcore import printcore
core = printcore(serial_port, baud_rate)
core.loud = True

recvcb = core.recvcb
core.recvcb = received_msg_from_fw

PORT = 8000
import SocketServer

httpd = SocketServer.TCPServer(("", PORT), TreeDeePrinterRequestHandler)
httpd.allow_reuse_address=True

print "serving at port", PORT
httpd.serve_forever()
