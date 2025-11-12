#Dependencia para hacer un blueprint/paquete
from flask import Blueprint

#Definir paquete de productos
admin_blueprint = Blueprint ('administrador', __name__, url_prefix ='/administrador', template_folder = 'templates')

from . import routes