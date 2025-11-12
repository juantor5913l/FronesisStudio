#Dependencia para hacer un blueprint/paquete
from flask import Blueprint

#Definir paquete de productos
cliente_blueprint = Blueprint ('cliente', __name__, url_prefix ='/cliente', template_folder = 'templates')

from . import routes