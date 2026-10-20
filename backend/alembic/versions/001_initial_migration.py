"""Initial migration - create all tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('student', 'admin', name='userrole'), nullable=False, server_default='student'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create study_profiles table
    op.create_table(
        'study_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('class_level', sa.String(length=50), nullable=False),
        sa.Column('stream', sa.String(length=100), nullable=False),
        sa.Column('study_hours_per_day', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('subjects', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('weak_subjects', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_study_profiles_id'), 'study_profiles', ['id'], unique=False)

    # Create subject_progress table
    op.create_table(
        'subject_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=100), nullable=False),
        sa.Column('mastery_percentage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_topics', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('weak_areas', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('last_studied', sa.DateTime(), nullable=True),
        sa.Column('total_study_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'subject', name='uq_user_subject_progress')
    )
    op.create_index(op.f('ix_subject_progress_id'), 'subject_progress', ['id'], unique=False)
    op.create_index('ix_user_subject', 'subject_progress', ['user_id', 'subject'], unique=False)

    # Create study_plans table
    op.create_table(
        'study_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('plan_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('generated_by_ai', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_study_plans_id'), 'study_plans', ['id'], unique=False)
    op.create_index('ix_user_date_active', 'study_plans', ['user_id', 'date', 'is_active'], unique=False)

    # Create study_plan_blocks table
    op.create_table(
        'study_plan_blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=100), nullable=False),
        sa.Column('topic', sa.String(length=255), nullable=False),
        sa.Column('minutes', sa.Integer(), nullable=False),
        sa.Column('task_description', sa.Text(), nullable=False),
        sa.Column('is_weak_subject', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['plan_id'], ['study_plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_study_plan_blocks_id'), 'study_plan_blocks', ['id'], unique=False)

    # Create quizzes table
    op.create_table(
        'quizzes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=100), nullable=False),
        sa.Column('topic', sa.String(length=255), nullable=False),
        sa.Column('difficulty', sa.String(length=50), nullable=False, server_default='medium'),
        sa.Column('questions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('generated_by_ai', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('source_material', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quizzes_id'), 'quizzes', ['id'], unique=False)
    op.create_index(op.f('ix_quizzes_subject'), 'quizzes', ['subject'], unique=False)

    # Create quiz_attempts table
    op.create_table(
        'quiz_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=100), nullable=False),
        sa.Column('answers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('correct_count', sa.Integer(), nullable=False),
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('time_taken_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_attempts_id'), 'quiz_attempts', ['id'], unique=False)
    op.create_index('ix_user_subject_date', 'quiz_attempts', ['user_id', 'subject', 'created_at'], unique=False)

    # Create user_streaks table
    op.create_table(
        'user_streaks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('current_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('longest_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_active_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_streaks_id'), 'user_streaks', ['id'], unique=False)

    # Create ai_content_generations table
    op.create_table(
        'ai_content_generations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('generation_type', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=100), nullable=False),
        sa.Column('topic', sa.String(length=255), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('model_used', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_content_generations_id'), 'ai_content_generations', ['id'], unique=False)
    op.create_index('ix_user_generation_type', 'ai_content_generations', ['user_id', 'generation_type'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_generation_type', table_name='ai_content_generations')
    op.drop_index(op.f('ix_ai_content_generations_id'), table_name='ai_content_generations')
    op.drop_table('ai_content_generations')

    op.drop_index(op.f('ix_user_streaks_id'), table_name='user_streaks')
    op.drop_table('user_streaks')

    op.drop_index('ix_user_subject_date', table_name='quiz_attempts')
    op.drop_index(op.f('ix_quiz_attempts_id'), table_name='quiz_attempts')
    op.drop_table('quiz_attempts')

    op.drop_index(op.f('ix_quizzes_subject'), table_name='quizzes')
    op.drop_index(op.f('ix_quizzes_id'), table_name='quizzes')
    op.drop_table('quizzes')

    op.drop_index(op.f('ix_study_plan_blocks_id'), table_name='study_plan_blocks')
    op.drop_table('study_plan_blocks')

    op.drop_index('ix_user_date_active', table_name='study_plans')
    op.drop_index(op.f('ix_study_plans_id'), table_name='study_plans')
    op.drop_table('study_plans')

    op.drop_index('ix_user_subject', table_name='subject_progress')
    op.drop_index(op.f('ix_subject_progress_id'), table_name='subject_progress')
    op.drop_table('subject_progress')

    op.drop_index(op.f('ix_study_profiles_id'), table_name='study_profiles')
    op.drop_table('study_profiles')

    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS userrole')