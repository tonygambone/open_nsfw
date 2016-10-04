#!/usr/bin/env python
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import sqlite3, urlparse, os, os.path, Image, tempfile, shutil

PORT_NUMBER = 9900
tempdir = tempfile.mkdtemp()

class AppHandler(BaseHTTPRequestHandler):	
    def do_GET(self):
        conn = sqlite3.connect('files.db')
        cursor = conn.cursor()
        url = urlparse.urlparse(self.path)
        query = urlparse.parse_qs(url.query)

        if url.path == '/':            
            self.send_response(200)
            self.send_header('Content-type','text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write('<style>div{display:inline-block;margin:8px;position:relative;}button{position:absolute;z-index:1;right:0;opacity:0.5;}</style>')
            self.wfile.write('<script>function reject(el,id){fetch("/reject?id="+id,{method:"POST"});el.parentNode.remove();}</script>')
            cursor.execute('select rowid from file_scores where confirmed != 0 order by score desc limit 100')
            for row in cursor:
                self.wfile.write('<div class="image"><a href="/img?id=%(rowid)s"><img src="/thumb?id=%(rowid)s"></a><button onclick="return reject(this,%(rowid)s);">x</button></div>' % { 'rowid': row[0] })            
        elif url.path == '/img':
            if not query.has_key('id'):
                self.send_error(404, 'Not found')
            else:
                rowid = query['id'][0]
                cursor.execute('select filename from file_scores where rowid = ?', [rowid])
                filename = cursor.fetchone()[0]
                if filename is None:
                    self.send_error(404, 'Not found')
                else:
                    mimetypes = {
                        '.jpg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif'
                    }
                    name, ext = os.path.splitext(filename)
                    f = open(filename) 
                    self.send_response(200)
                    self.send_header('Content-type', mimetypes[ext.lower()])
                    self.send_header('Cache-control', 'max-age=86400')
                    self.end_headers()
                    self.wfile.write(f.read())
                    f.close()
        elif url.path == '/thumb':
            if not query.has_key('id'):
                self.send_error(404, 'Not found')
            else:
                rowid = query['id'][0]
                cursor.execute('select filename from file_scores where rowid = ?', [rowid])
                filename = cursor.fetchone()[0]
                thumbnail_path = os.path.join(tempdir, rowid)
                if filename is None or not os.path.exists(filename):
                    self.send_error(404, 'Not found')
                elif not os.path.exists(thumbnail_path):
                    image = Image.open(filename)
                    image.thumbnail((300,300), Image.ANTIALIAS)
                    self.send_response(200)
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Cache-control', 'max-age=86400')
                    self.end_headers()
                    image.save(thumbnail_path, "JPEG")
                    image.save(self.wfile, "JPEG")
                else:
                    f = open(thumbnail_path)
                    self.send_response(200)
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Cache-control', 'max-age=86400')
                    self.end_headers()
                    self.wfile.write(f.read())
                    f.close()
        else:
            self.send_error(404, 'Not found')
        conn.close()
    
    def do_POST(self):
        conn = sqlite3.connect('files.db')
        cursor = conn.cursor()
        url = urlparse.urlparse(self.path)
        query = urlparse.parse_qs(url.query)

        if url.path == '/reject':
            if not query.has_key('id'):
                self.send_error(404, 'Not found')
            else:
                rowid = query['id'][0]
                cursor.execute('update file_scores set confirmed = 0 where rowid = ?', [rowid])
                conn.commit()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write('{"id": %s, "confirmed": 0 }' % rowid)
        else:
            self.send_error(404, 'Not found')
        conn.close()

if __name__ == '__main__':                
    try:
        server = HTTPServer(('', PORT_NUMBER), AppHandler)
        print 'Server running on port %d' % PORT_NUMBER
        print 'Using tempdir %s' % tempdir
        server.serve_forever()

    except KeyboardInterrupt:
        print 'Interrupt received. Exiting.'
        server.socket.close()
        shutil.rmtree(tempdir, True)