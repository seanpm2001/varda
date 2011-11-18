"""
Models backed by SQL using SQLAlchemy.
"""


from datetime import date

from sqlalchemy import Index

from varda import db


class Variant(db.Model):
    """
    Genomic variant.
    """
    id = db.Column(db.Integer, primary_key=True)
    chromosome = db.Column(db.String(2))
    begin = db.Column(db.Integer)
    end = db.Column(db.Integer)
    reference = db.Column(db.String(200))
    variant = db.Column(db.String(200))

    def __init__(self, chromosome, begin, end, reference, variant):
        self.chromosome = chromosome
        self.begin = begin
        self.end = end
        self.reference = reference
        self.variant = variant

    def __repr__(self):
        return '<Variant chr%s:%i %s>' % (
            self.chromosome, self.begin, self.variant)

    def to_dict(self):
        return {'id':         self.id,
                'chromosome': self.chromosome,
                'begin':      self.begin,
                'end':        self.end,
                'reference':  self.reference,
                'variant':    self.variant}


Index('index_variant_position',
      Variant.chromosome, Variant.begin, Variant.end)
Index('index_variant_unique',
      Variant.chromosome, Variant.begin, Variant.end,
      Variant.reference, Variant.variant, unique=True)


class Population(db.Model):
    """
    Population study.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    added = db.Column(db.Date)
    size = db.Column(db.Integer)

    def __init__(self, name, size=0):
        self.name = name
        self.size = size
        self.added = date.today()

    def __repr__(self):
        return '<Population %r>' % self.name

    def to_dict(self):
        return {'id':    self.id,
                'name':  self.name,
                'added': str(self.added),
                'size':  self.size}


class MergedObservation(db.Model):
    """
    Observation in a population.

    Todo: Add genotype.
    """
    population_id = db.Column(db.Integer, db.ForeignKey('population.id'), primary_key=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('variant.id'), primary_key=True)
    support = db.Column(db.Integer)

    population = db.relationship(Population, backref=db.backref('merged_observations', lazy='dynamic'))
    variant = db.relationship(Variant, backref=db.backref('merged_observations', lazy='dynamic'))

    def __init__(self, population, variant, support=0):
        self.population = population
        self.variant = variant
        self.support = support

    def __repr__(self):
        return '<MergedObservation %s %r %i>' % (self.population.name, self.variant, self.support)

    def to_dict(self):
        return {'population': self.population.id,
                'variant':    self.variant.id,
                'support':    self.support}


class Sample(db.Model):
    """
    Sample.

    Todo: do we still need a poolSize in Sample now that we split population
    studies to a separate model?
    """
    id = db.Column(db.Integer, primary_key=True)
    threshold = db.Column(db.Integer)
    added = db.Column(db.Date)
    comment = db.Column(db.String(200))

    def __init__(self, threshold=None, comment=None):
        self.threshold = threshold
        self.comment = comment
        self.added = date.today()

    def __repr__(self):
        return '<Sample %r>' % self.id

    def to_dict(self):
        return {'id':        self.id,
                'threshold': self.threshold,
                'added':     str(self.added),
                'comment':   self.comment}


class Observation(db.Model):
    """
    Observation in a sample
    """
    sample_id = db.Column(db.Integer, db.ForeignKey('sample.id'), primary_key=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('variant.id'), primary_key=True)
    coverage = db.Column(db.Integer)
    support = db.Column(db.Integer)

    sample = db.relationship(Sample, backref=db.backref('observations', lazy='dynamic'))
    variant = db.relationship(Variant, backref=db.backref('observations', lazy='dynamic'))

    def __init__(self, sample, variant, coverage=None, support=None):
        self.sample = sample
        self.variant = variant
        self.coverage = coverage
        self.support = support

    def __repr__(self):
        return '<Observation %i %r %i %i>' % (self.sample.id, self.variant, self.coverage, self.support)

    def to_dict(self):
        return {'sample':   self.sample.id,
                'variant':  self.variant.id,
                'coverage': self.coverage,
                'support':  self.support}
