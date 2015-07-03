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
    )

from pyramid.security import (
    remember,
    forget,
    authenticated_userid,
    )

from remotetrain.security import USERS


# global variables.
from remotetrain.commander import Commander
g_Commander = Commander('/dev/ttyACM0', 9600)

from remotetrain.camera import CameraAPI
g_Camera = CameraAPI('wlan1')


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
    
    # initialize CameraAPI object
    global g_Camera
    g_Camera.reinitialize()
    
    return dict(logged_in = authenticated_userid(request))



@view_config(route_name='edit_page', 
             renderer='templates/edit.html', 
             permission='edit')
def edit_page(request):
    logged_in = authenticated_userid(request)
    settings = DBSession.query(ControllerSettings).filter_by(user=logged_in).first()
    
    # initialize CameraAPI object
    global g_Camera, g_Commander
    g_Camera.reinitialize()
    g_Commander.reinitialize()
    
    
    if settings is None:
        return HTTPNotFound('No such page')

    return dict(num_power_packs=settings.power_pack, num_turnouts=settings.turnout, num_feeders=3, logged_in=logged_in)



@view_config(route_name='update_control',
             renderer='json',
             permission='edit')
def update_control(request):

    json_data = request.json_body
    
    print(json_data)
    
    for k, v in json_data.items():
        g_Commander.send_command(k, v)

    return json_data


@view_config(route_name='camera_api',
             renderer='json',
             permission='edit')
def camera_api(request):

    json_data = request.json_body
    print(json_data)
    
    g_Camera.camera_api(json_data['method'], json_data['params'])
    
    return json_data

@view_config(route_name='avContent_api',
             renderer='json',
             permission='edit')
def avContent_api(request):

    json_data = request.json_body
    print(json_data)
    
    g_Camera.avContent_api(json_data['method'], json_data['params'])
    
    return json_data



