"""
High-level REST API unit tests.

Todo: Look at http://packages.python.org/Flask-Testing/
Todo: Suppress the annoying log messages.
"""


from StringIO import StringIO
import tempfile
import json

from nose.tools import *
import vcf

from varda import create_app, db
from varda.models import User


TEST_SETTINGS = {
    'TESTING': True,
    'FILES_DIR': tempfile.mkdtemp(),
    'SQLALCHEMY_DATABASE_URI': 'sqlite://',
    'BROKER_TRANSPORT': 'memory',
    'CELERY_ALWAYS_EAGER': True,
    'CELERY_EAGER_PROPAGATES_EXCEPTIONS': True
}


def auth_header(login='admin', password='test'):
    """
    HTTP Basic Authentication header for a test user.
    """
    user = '%s:%s' % (login, password)
    return ('AUTHORIZATION', 'BASIC ' + user.encode('base64'))


class TestApi():
    """
    High-level unit tests, using the REST API entry points of Varda.

    Todo: Split into several test classes.
    """
    def setup(self):
        """
        Run once before every test. Setup the test database.
        """
        self.app = create_app(TEST_SETTINGS)
        self.client = self.app.test_client()
        with self.app.test_request_context():
            db.create_all()
            admin = User('Test Admin', 'admin', 'test', roles=['admin'])
            db.session.add(admin)
            trader = User('Test Trader', 'trader', 'test', roles=['importer', 'trader'])
            db.session.add(trader)
            user = User('Test User', 'user', 'test', roles=[])
            db.session.add(user)
            db.session.commit()

    def teardown(self):
        """
        Run once after every test. Drop the test database.
        """
        with self.app.test_request_context():
            db.session.remove()
            db.drop_all()

    def test_root(self):
        """
        Dummy test.
        """
        r = self.client.get('/')
        assert 'contact' in r.data

    def test_parameter_type(self):
        """
        Test request with incorrect parameter type.
        """
        r = self.client.post('/data_sources/abc/annotations', headers=[auth_header()])
        assert_equal(r.status_code, 404)

    def test_authentication(self):
        """
        Test authentication stuff.
        """
        r = self.client.get('/users')
        assert_equal(r.status_code, 401)

        r = self.client.get('/users', headers=[auth_header(password='incorrect')])
        assert_equal(r.status_code, 401)

        r = self.client.get('/users', headers=[auth_header()])
        assert_equal(r.status_code, 200)

        r = self.client.get('/users', headers=[auth_header(login='user', password='test')])
        assert_equal(r.status_code, 403)

        r = self.client.get('/')
        assert_equal(r.status_code, 200)

        r = self.client.get('/', headers=[auth_header(login='user', password='test')])
        assert_equal(r.status_code, 200)

    def test_user(self):
        """
        Test user creation.
        """
        data = {'name': 'Test Tester',
                'login': 'test',
                'password': 'test',
                'roles': ''}
        r = self.client.post('/users', data=data, headers=[auth_header()])
        assert_equal(r.status_code, 201)
        # Todo: Something better than the replace.
        user = r.headers['Location'].replace('http://localhost', '')

        r = self.client.get(user, headers=[auth_header()])
        assert_equal(r.status_code, 200)

    def test_user_json(self):
        """
        Test user creation with a json payload.
        """
        data = {'name': 'Test Tester',
                'login': 'test',
                'password': 'test',
                'roles': ''}
        r = self.client.post('/users', data=json.dumps(data), content_type='application/json', headers=[auth_header()])
        assert_equal(r.status_code, 201)
        # Todo: Something better than the replace.
        user = r.headers['Location'].replace('http://localhost', '')

        r = self.client.get(user, headers=[auth_header()])
        assert_equal(r.status_code, 200)

    def test_exome(self):
        """
        Import and annotate exome sample with coverage track.

        All annotations should have observation and coverage 1.
        """
        _, vcf_data_source, _ = self._import('Test sample', 'tests/data/exome-samtools.vcf', 'tests/data/exome-samtools.bed')
        annotation = self._annotate(vcf_data_source)

        # Download annotation and see if we can parse it as VCF
        r = self.client.get(annotation, headers=[auth_header()])
        assert_equal(r.content_type, 'application/x-gzip')
        open('/tmp/test_exome.vcf.gz', 'w').write(r.data)
        for _ in vcf.Reader(StringIO(r.data), compressed=True):
            pass

    def test_exome_subset(self):
        """
        Import exome sample with coverage track and import and annotate a
        subset of it.

        All annotations should have observation and coverage 2.
        """
        self._import('Test sample', 'tests/data/exome-samtools.vcf', 'tests/data/exome-samtools.bed')
        _, vcf_data_source, _ = self._import('Test subset', 'tests/data/exome-samtools-subset.vcf', 'tests/data/exome-samtools-subset.bed')
        annotation = self._annotate(vcf_data_source)

        # Download annotation and see if we can parse it as VCF
        r = self.client.get(annotation, headers=[auth_header()])
        assert_equal(r.content_type, 'application/x-gzip')
        open('/tmp/test_exome_subset.vcf.gz', 'w').write(r.data)
        for _ in vcf.Reader(StringIO(r.data), compressed=True):
            pass

    def test_exome_superset(self):
        """
        Import exome sample with coverage track and import and annotate a
        superset of it.

        All annotations should have observation and coverage (2, 2), (1, 2), or (1, 1).
        """
        _, vcf_data_source, _ = self._import('Test sample', 'tests/data/exome-samtools.vcf', 'tests/data/exome-samtools.bed')
        self._import('Test subset', 'tests/data/exome-samtools-subset.vcf', 'tests/data/exome-samtools-subset.bed')
        annotation = self._annotate(vcf_data_source)

        # Download annotation and see if we can parse it as VCF
        r = self.client.get(annotation, headers=[auth_header()])
        assert_equal(r.content_type, 'application/x-gzip')
        open('/tmp/test_exome_superset.vcf.gz', 'w').write(r.data)
        for _ in vcf.Reader(StringIO(r.data), compressed=True):
            pass

    def test_trader(self):
        """
        A trader can only annotate after importing.
        """
        # Create sample
        data = {'name': 'Test sample',
                'coverage_threshold': 8,
                'pool_size': 1}
        r = self.client.post('/samples', data=data, headers=[auth_header(login='trader', password='test')])
        assert_equal(r.status_code, 201)
        sample = json.loads(r.data)['sample']

        # Upload VCF
        data = {'name': 'Test observations',
                'filetype': 'vcf',
                'data': open('tests/data/exome-samtools.vcf')}
        r = self.client.post('/data_sources', data=data, headers=[auth_header(login='trader', password='test')])
        assert_equal(r.status_code, 201)
        # Todo: Something better than the replace.
        vcf_data_source = r.headers['Location'].replace('http://localhost', '')

        # Get annotations URI for the observations data source
        r = self.client.get(vcf_data_source, headers=[auth_header(login='trader', password='test')])
        assert_equal(r.status_code, 200)
        annotations = json.loads(r.data)['data_source']['annotations']

        # Annotate observations
        r = self.client.post(annotations, headers=[auth_header(login='trader', password='test')])
        assert_equal(r.status_code, 400)

        # Get observations URIs for this sample
        r = self.client.get(sample, headers=[auth_header(login='trader', password='test')])
        observations = json.loads(r.data)['sample']['observations']

        # Import observations
        data = {'data_source': vcf_data_source}
        r = self.client.post(observations, data=data, headers=[auth_header(login='trader', password='test')])
        assert_equal(r.status_code, 202)
        observations_wait = json.loads(r.data)['wait']

        # Annotate observations
        r = self.client.post(annotations, headers=[auth_header(login='trader', password='test')])
        assert_equal(r.status_code, 202)

    def _annotate(self, vcf_data_source):
        """
        Annotate observations and return the annotation URI.
        """
        # Get annotations URI for the observations data source
        r = self.client.get(vcf_data_source, headers=[auth_header()])
        assert_equal(r.status_code, 200)
        annotations = json.loads(r.data)['data_source']['annotations']

        # Annotate observations
        r = self.client.post(annotations, headers=[auth_header()])
        assert_equal(r.status_code, 202)
        annotation_wait = json.loads(r.data)['wait']
        # Note: This API diverges only for the unit test setting
        annotation = json.loads(r.data)['annotation']['uri']

        # Fake check (all results are direct in the unit test setting)
        r = self.client.get(annotation_wait, headers=[auth_header()])
        assert_equal(r.status_code, 200)
        ok_(json.loads(r.data)['annotation']['ready'])

        return annotation

    def _import(self, name, vcf_file, bed_file):
        """
        Import observations and coverage. Return a tuple with URIs for the
        sample, VCF data source, and BED data source.
        """
        # Create sample
        data = {'name': name,
                'coverage_threshold': 8,
                'pool_size': 1}
        r = self.client.post('/samples', data=data, headers=[auth_header()])
        assert_equal(r.status_code, 201)
        sample = json.loads(r.data)['sample']

        # Upload VCF
        data = {'name': '%s observations' % name,
                'filetype': 'vcf',
                'data': open(vcf_file)}
        r = self.client.post('/data_sources', data=data, headers=[auth_header()])
        assert_equal(r.status_code, 201)
        # Todo: Something better than the replace.
        vcf_data_source = r.headers['Location'].replace('http://localhost', '')

        # Upload BED
        data = {'name': '%s coverage' % name,
                'filetype': 'bed',
                'data': open(bed_file)}
        r = self.client.post('/data_sources', data=data, headers=[auth_header()])
        assert_equal(r.status_code, 201)
        # Todo: Something better than the replace.
        bed_data_source = r.headers['Location'].replace('http://localhost', '')

        # Get observations and regions URIs for this sample
        r = self.client.get(sample, headers=[auth_header()])
        observations = json.loads(r.data)['sample']['observations']
        regions = json.loads(r.data)['sample']['regions']

        # Import observations
        data = {'data_source': vcf_data_source}
        r = self.client.post(observations, data=data, headers=[auth_header()])
        assert_equal(r.status_code, 202)
        observations_wait = json.loads(r.data)['wait']

        # Fake check (all results are direct in the unit test setting)
        r = self.client.get(observations_wait, headers=[auth_header()])
        assert_equal(r.status_code, 200)
        ok_(json.loads(r.data)['observations']['ready'])

        # Import regions
        data = {'data_source': bed_data_source}
        r = self.client.post(regions, data=data, headers=[auth_header()])
        assert_equal(r.status_code, 202)
        regions_wait = json.loads(r.data)['wait']

        # Fake check (all results are direct in the unit test setting)
        r = self.client.get(regions_wait, headers=[auth_header()])
        assert_equal(r.status_code, 200)
        ok_(json.loads(r.data)['regions']['ready'])

        return sample, vcf_data_source, bed_data_source

    def test_import_1kg(self):
        """
        Import 1000 genomes variants.
        """
        return  # disabled due to population-study refactoring
        # Create sample
        data = {'name': '1KG',
                'coverage_threshold': 6,
                'pool_size': 1092}
        r = self.client.post('/samples', data=data, headers=[auth_header()])
        assert_equal(r.status_code, 201)
        sample = json.loads(r.data)['sample']

        # Get observations URI for this sample
        r = self.client.get(sample, headers=[auth_header()])
        observations = json.loads(r.data)['sample']['observations']

        # Upload VCF
        data = {'name': 'Some variants',
                'filetype': 'vcf',
                'data': open('tests/data/1kg.vcf')}
        r = self.client.post('/data_sources', data=data, headers=[auth_header()])
        assert_equal(r.status_code, 201)
        # Todo: Something better than the replace.
        data_source = r.headers['Location'].replace('http://localhost', '')

        # Import VCF
        data = {'data_source': data_source}
        r = self.client.post(observations, data=data, headers=[auth_header()])
        assert_equal(r.status_code, 202)
        wait = json.loads(r.data)['wait']

        # Check success
        r = self.client.get(wait, headers=[auth_header()])
        assert_equal(r.status_code, 200)
        ok_(json.loads(r.data)['observations']['ready'])
