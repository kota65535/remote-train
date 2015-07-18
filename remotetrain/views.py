# from pyramid.response import Response
from pyramid.view import (
    view_config,
    forbidden_view_config,
    )

from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    )

from sqlalchemy.exc import DBAPIError

from remotetrain.models import (
    DBSession,
    ControllerSettings,
    DeviceSettings
    )

from pyramid.security import (
    remember,
    forget,
    authenticated_userid,
    )

from remotetrain.security import USERS

# global variables.
from remotetrain.commander import Commander
g_Commander = None
# Commander('/dev/ttyACM0', 9600)

from remotetrain.camera import CameraAPI
g_Camera = None
# CameraAPI('wlan1')

import logging
logger = logging.getLogger(__name__)


class CameraUnavailableError(Exception):
    pass

class ControllerUnavailableError(Exception):
    pass


@view_config(route_name='home', 
             renderer='templates/home.html')
def home(request):
    return dict()


@view_config(route_name='login', 
             renderer='templates/login.html')
@forbidden_view_config(renderer='templates/login.html')
def login(request):
    login_url = request.route_url('login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/' # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)
    message = 'You need to login to proceed.'
    login = ''
    password = ''
    if 'form-signin.submitted' in request.params:
        login = request.params['login']
        password = request.params['password']
        if USERS.get(login) == password:
            headers = remember(request, login)
            return HTTPFound(location = came_from,
                             headers = headers)
        else:
            message = 'Failed login'

    return dict(
        message = message,
        url = request.application_url + '/login',
        came_from = came_from,
        login = login,
        password = password,
        )


@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location = request.route_url('home'),
                     headers = headers)


@view_config(route_name='view_page', 
             renderer='templates/view.html', 
             permission='view')
def view_page(request):
    logged_in = authenticated_userid(request)
    camera_conf = DBSession.query(DeviceSettings).filter_by(user=logged_in).first()
    
    if camera_conf is None:
        return HTTPNotFound("Camera configuration is missing!")
    
    # カメラAPIオブジェクトの初期化
    global g_Camera
    g_Camera = CameraAPI(camera_conf.interface)
    
    if g_Camera.is_available:
        return dict(logged_in)
    else:
        raise CameraUnavailableError
    

@view_config(context=CameraUnavailableError,
             renderer='templates/error.html')
def camera_error_page(exc, request):
    return dict(logged_in = authenticated_userid(request),
                message="Sorry, camera is not available now.")


@view_config(route_name='controller_page', 
             renderer='templates/controller.html', 
             permission='edit')
def controller_page(request):
    logged_in = authenticated_userid(request)
    controller_conf = DBSession.query(ControllerSettings).filter_by(user=logged_in).first()
    
    if controller_conf is None:
        return HTTPNotFound("Controller configuration is missing!")
        
    global g_Commander
    g_Commander = Commander(controller_conf.serial_device, 9600)
    
    if g_Commander.is_available:
        return dict(num_power_packs=controller_conf.power_pack,
                    num_turnouts=controller_conf.turnout, 
                    num_feeders=controller_conf.feeder, 
                    logged_in=logged_in)
    else:
        raise ControllerUnavailableError
    

@view_config(context=ControllerUnavailableError,
             renderer='templates/error.html')
def controller_error_page(exc, request):
    return dict(logged_in = authenticated_userid(request),
                message="Sorry, controller is not available now.")



@view_config(route_name='viewcon_page', 
             renderer='templates/viewcon.html', 
             permission='edit')
def viewcon_page(request):
    logged_in = authenticated_userid(request)
    camera_conf = DBSession.query(DeviceSettings).filter_by(user=logged_in).first()
    controller_conf = DBSession.query(ControllerSettings).filter_by(user=logged_in).first()
    
    if controller_conf is None:
        return HTTPNotFound("Controller configuration is missing.")
    
    global g_Camera, g_Commander
    g_Camera = CameraAPI(camera_conf.interface)
    g_Commander = Commander(controller_conf.serial_device, 9600)
    
    
    if not g_Camera.is_available:
        raise CameraUnavailableError
    if not g_Commander.is_available:
        raise ControllerUnavailableError
         
    return dict(num_power_packs=controller_conf.power_pack,
                num_turnouts=controller_conf.turnout, 
                num_feeders=controller_conf.feeder, 
                logged_in=logged_in)


@view_config(route_name='update_control',
             renderer='json',
             permission='edit')
def update_control(request):

    json_data = request.json_body
    
    logger.debug(json_data)
    
    for k, v in json_data.items():
        g_Commander.send_command(k, v)

    return json_data


@view_config(route_name='camera_api',
             renderer='json',
             permission='edit')
def camera_api(request):

    json_data = request.json_body
    logger.debug(json_data)
    
    g_Camera.camera_api(json_data['method'], json_data['params'])
    
    return json_data


@view_config(route_name='avContent_api',
             renderer='json',
             permission='edit')
def avContent_api(request):

    json_data = request.json_body
    logger.debug(json_data)
    
    g_Camera.avContent_api(json_data['method'], json_data['params'])
    
    return json_data



