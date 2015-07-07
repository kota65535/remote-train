import logging
import sys
import os

def getLogger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    fh = logging.FileHandler("test.log", "a+")
    logger.addHandler(fh)
#     logger.addHandler(handler)
    
    return logger

