import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

from remotetrain.models import (
    DBSession,
    ControllerSettings,
    CameraSettings,
    )


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    with transaction.manager:
        controller_conf = ControllerSettings(user='editor',
                                             serial_device='/dev/ttyACM0',
                                             power_pack=2, 
                                             turnout=10, 
                                             feeder=3)
        DBSession.add(controller_conf)
        camera_conf = CameraSettings(user='editor', 
                                     interface='wlan1')
        DBSession.add(camera_conf)
        camera_conf = CameraSettings(user='viewer', 
                                     interface='wlan1')
        DBSession.add(camera_conf)
        
    
