## config/const.py

from config.settings import config

JOB_VACANCY_CHANNEL = "job_seek"

CV_BASE_PATH = config.BASE_DIR / "data" / "cv"

TEMPLATE_BASE_PATH = config.BASE_DIR / "data" / "template"

FEMALE_KEYWORDS = {"female", "perempuan", "wanita"}

MALE_KEYWORDS = {"male", "men", "laki-laki", "pria"}