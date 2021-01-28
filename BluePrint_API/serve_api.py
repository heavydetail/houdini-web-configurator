#!/usr/bin/python
# coding: latin-1

from flask import Flask, jsonify
from flask import make_response
from flask import request
from flask_cors import CORS
from datetime import datetime
from time import time

import hou
import array
import sys
import getopt
import os
import json
import uuid
import os.path


def enableHouModule():
    '''
    Set up the environment so that "import hou" works.
    '''
    if hasattr(sys, "setdlopenflags"):
        old_dlopen_flags = sys.getdlopenflags()
        import DLFCN
        sys.setdlopenflags(old_dlopen_flags | DLFCN.RTLD_GLOBAL)

    try:
        import hou
    except ImportError:
        sys.path.append(
            os.environ['HFS'] + "/houdini/python%d.%dlibs" % sys.version_info[:2])
        import hou
    finally:
        if hasattr(sys, "setdlopenflags"):
            sys.setdlopenflags(old_dlopen_flags)


enableHouModule()

app = Flask(__name__, instance_path='C:/')
app.debug = True
CORS(app)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.route("/")
def hello():
    return "Hello from Houdini Pipe API!"


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route("/regenerate", methods=['POST'])
def houdini_regenerate():
    """
    Call Houdini HIP/HDA with JSON parameters replacing the asset parameters, exports new GLTF file.
    """
    x = 1.0
    y = 1.0
    z = 1.0
    render = False

    # Parse JSON Arguments into Parameter Variables:
#    if not request.json:
 #       abort(400)

    hda = request.json.get('hda')
    x = float(request.json.get('sizex'))
    y = float(request.json.get('sizey'))
    z = float(request.json.get('sizez'))
    render = bool(request.json.get('render'))

    print("Read these Arguments X: {} Y: {} Z: {}".format(x, y, z))
    print("Rendering is set to: {}".format(render))

    # Which HDA / Project File (HIP) to serve:
    hou.hipFile.load("./{0}.hip".format(hda))

    # Get References for our Operations
    geonode = hou.node("/obj/geo1/GEO_OUT")
    geo = geonode.geometry()

    # Change Asset Parameters
    objnode = hou.node("/obj/geo1/box1")
    xparm = objnode.parm("sizex")
    yparm = objnode.parm("sizey")
    zparm = objnode.parm("sizez")
    xparm.set(x)
    yparm.set(y)
    zparm.set(z)

    # Re-Cook the Nodes (not needed?)
    # objnode.cook(True, 0)

    # Output the Volume Attribute
    volattrib = hou.Geometry.findPrimAttrib(geo, "volume")
    volume = hou.Geometry.primFloatAttribValues(geo, "volume")  # AsString
    # print(volume)
    if len(volume) > 0:
        print("Object {0} is: {1:.2f} unit^3 (meters)".format(
            volattrib.name(), volume[0]))

    # For OBJs if needed to debug etc.:
    # geo.saveToFile("geoexport/export_{}.obj".format(time()))
    #print("Saved OBJ file to geoexport Folder.")

    # Render ROPs, mantra is slow, so disable if not needed. Could be used for project preview thumbs.
    if(render):
        renderOutputNode("/out/mantra1")

    # Customize ROP Path:
    rop_path = hou.node("/out/gltf1").parm("file")
    filename = "gltf1.{0}.glb".format(uuid.uuid4())
    filepath = "../BluePrint_Builder/geo/"+filename

    rop_path.set(filepath)

    renderOutputNode("/out/gltf1")

    return jsonify({'volume': volume[0], 'timestamp': format(time()), 'gltf_filename': filename})


@app.route("/getGLTFfile/<string:filename>", methods=['GET'])
def getGLTFfile(filename):
    '''
    # TODO: Read file and send to client (if possible)
    '''
    if filename == "":
        InvalidUsage("No UUID supplied.", status_code=410)

    filepath = "../BluePrint_Builder/geo/"+filename
    if os.path.isfile(filepath):
        return "GLTF File exists."
    else:
        return "Not Found."


def renderOutputNode(path):
    node = hou.node(path)
    print("Starting render of output node " + node.name())
    node.render()
    print("Finished render of output node " + node.name())


@app.errorhandler(InvalidUsage)
def handle_InvalidUsage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


if __name__ == "__main__":
    app.run(debug=True)
