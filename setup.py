import setuptools as st
import os

# Utility function to read the README file.  Used for the
# long_description.  It's easier to maintain README file than to put a
# raw string below. The readme file is assumed to be in the same
# directory as setup.py

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

st.setup(name='pyemread',
         version='0.1.0',
         description='Eye tracking tools.',
         long_description=read('README.md'),
         url='https://github.com/gtojty/pyemread',
         author='Tao Gong; Dave Braze',
         author_email='gtojty@gmail.com; davebraze@gmail.com',
         license='MIT',
         keywords=['eye-tracking', 'data processing', 'stimulus generation'],
         packages=st.find_packages(), # List directories containing package source code.
         zip_safe=False,
         platforms='any',   # As a source package, this should be safe.
         install_requires=[ # List package dependencies here. Only
                            # include those that are not part of the
                            # python standard library
             'turtle',
             'pandas',
             'numpy',
             'Pillow',
             'matplotlib'
         ],
         classifiers=[
             'Development Status :: 4 - Beta',
             'Intended Audience :: Science/Research',
             'License :: OSI Approved :: MIT License',
             'Natural Language :: English',
             'Programming Language :: Python',
             'Topic :: Scientific/Engineering'
         ]
)
