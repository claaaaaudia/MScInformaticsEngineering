import hashlib

_image_cache = {}

def pipeline_hash(pipeline):
    return hashlib.sha256(str(pipeline).encode()).hexdigest()

def get_cached(project_id, pipeline):
    return _image_cache.get((project_id, pipeline_hash(pipeline)))

def set_cached(project_id, pipeline, image):
    _image_cache[(project_id, pipeline_hash(pipeline))] = image
