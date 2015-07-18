from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from remotetrain.security import groupfinder


from remotetrain.models import (
    DBSession,
    Base,
    )


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    
    config = Configurator(settings=settings, 
                          root_factory='remotetrain.models.RootFactory')
    config.include('pyramid_mako')
    config.add_mako_renderer('.html')
    
    authn_policy = AuthTktAuthenticationPolicy('sosecret', callback=groupfinder, hashalg='sha512')
    authz_policy = ACLAuthorizationPolicy()
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)

    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('liveview', 'liveview', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('view_page', '/view_page')
    config.add_route('controller_page', '/controller_page')
    config.add_route('viewcon_page', '/viewcon_page')
    config.add_route('update_control', '/update_control')
    config.add_route('camera_api', '/camera_api')
    config.add_route('avContent_api', '/avContent_api')
    config.scan()
    return config.make_wsgi_app()
