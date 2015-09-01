"""Add annotation queries

Revision ID: 1d808cef0787
Revises: 1c15bafd311a
Create Date: 2015-08-17 14:31:52.751784

"""

# revision identifiers, used by Alembic.
revision = '1d808cef0787'
down_revision = '1c15bafd311a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('query',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=True),
    sa.Column('expression', sa.Text(), nullable=True),
    sa.Column('require_active', sa.Boolean(), nullable=True),
    sa.Column('require_coverage_profile', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8',
    mysql_engine='InnoDB'
    )
    op.create_table('annotation_query',
    sa.Column('annotation_id', sa.Integer(), nullable=False),
    sa.Column('query_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['annotation_id'], ['annotation.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['query_id'], ['query.id'], ondelete='CASCADE')
    )
    op.drop_table('sample_frequency')
    op.drop_column('annotation', 'global_frequency')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('annotation', sa.Column('global_frequency', sa.BOOLEAN(), nullable=True))
    op.create_table('sample_frequency',
    sa.Column('annotation_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('sample_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['annotation_id'], [u'annotation.id'], name=u'sample_frequency_annotation_id_fkey', ondelete=u'CASCADE'),
    sa.ForeignKeyConstraint(['sample_id'], [u'sample.id'], name=u'sample_frequency_sample_id_fkey', ondelete=u'CASCADE')
    )
    op.drop_table('query')
    op.drop_table('annotation_query')
    ### end Alembic commands ###
