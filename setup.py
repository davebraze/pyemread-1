from setuptools import setup find_packages

# Utility function to read the README file.  Used for the
# long_description.  It's easier to maintain README file than to put a
# raw string below. The readme file is assumed to be in the same
# directory as setup.py

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='emf_rp',
      version='0.1.0',
      description='Eye tracking tools.',
      long_description=read('README.md'),
      url='https://github.com/gtojty/emf_rp',
      author='Tao Gong; Dave Braze',
      author_email='davebraze@gmail.com',
      license='MIT',
      keywords="eye-tracking data processing gaze",
      packages=find_packages(),
      zip_safe=False)
