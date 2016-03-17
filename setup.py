from setuptools import setup
import nvm

install_requirements = ['nose>=1.3.7',
                        'cffi>=1.0.0']

setup_requirements = ['cffi>=1.0.0',
                      'nose>=1.3.1',
                      'coveralls>=1.1',
                      'mock']

setup(
    name='pynvm',
    version=nvm.__version__,
    url='https://github.com/perone/pynvm',
    license='BSD 3-clause',
    author=nvm.__author__,
    author_email='christian.perone@gmail.com',
    description='Next-generation non-volatile memory for Python.',
    long_description='Next-generation non-volatile memory for Python.',
    install_requires=install_requirements,
    setup_requires=setup_requirements,
    cffi_modules=["nvm/libex.py:ffi"],
    test_suite="nose.collector",
    packages=['nvm'],
    keywords='nvm, scm, non-volatile memory, nvml, nvm library, pmem, dax',
    platforms='Any',
    zip_safe=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
