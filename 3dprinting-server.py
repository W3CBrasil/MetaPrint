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
def executa_fatiamento(slicecommand):
#  try:
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
#  except:
#    print "Failed to execute slicing software"

slicer_executable = "Slic3r_gnulinux/bin/slic3r"
printer_path = "profiles/printer"
print_path = "profiles/print"
filament_path = "profiles/filament"
support_material = False
fill_density = 0.2

if support_material:
  support_material_param = "--support_material"
else:
  support_material_param = ""

def invoke_3d_print_job(path):
  print "We will print this file:", path
  input_file = os.getcwd() + path
  output_file = os.getcwd() + "/output.gcode" #TODO: generate it based on input filename
  printer_profile = "Metamaquina2" #TODO: let the user decide
  print_profile = "Padrao" #TODO: let the user decide
  filament_profile = "PLA" #TODO: let the user decide

  slicecommand = "%s --load %s/%s.ini --load %s/%s.ini --load %s/%s.ini --fill-density %s %s %s --output %s" % (slicer_executable, printer_path, printer_profile, print_path, print_profile, filament_path, filament_profile, str(fill_density), support_material_param, input_file, output_file)
  print "We'll slice it with the following command: ", slicecommand
  executa_fatiamento(slicecommand)

__version__ = "0.6"

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

    def do_GET(self):
        """Serve a GET request."""

        if self.path.startswith("/print"):
          invoke_3d_print_job(self.path.split("/print")[1])
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


PORT = 8000
import SocketServer

httpd = SocketServer.TCPServer(("", PORT), TreeDeePrinterRequestHandler)
httpd.allow_reuse_address=True

print "serving at port", PORT
httpd.serve_forever()
