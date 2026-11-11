"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-11

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("make", sa.String(100)),
        sa.Column("model", sa.String(100)),
        sa.Column("purchase_date", sa.Date()),
        sa.Column("tank_capacity_l", sa.Numeric(4, 2), nullable=False, server_default="13.00"),
        sa.Column("initial_odometer_km", sa.Numeric(7, 1), nullable=False, server_default="0.0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )

    op.create_table(
        "fuel_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False, index=True
        ),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("odometer_km", sa.Numeric(7, 1)),
        sa.Column("litres", sa.Numeric(5, 2), nullable=False),
        sa.Column("amount_rs", sa.Numeric(9, 2)),
        sa.Column("price_per_litre", sa.Numeric(6, 2)),
        sa.Column("fill_type", sa.String(10)),
        sa.Column("location", sa.String(100), index=True),
        sa.Column("station_name", sa.String(150)),
        sa.Column("notes", sa.Text()),
        sa.Column("odometer_status", sa.String(10), nullable=False, server_default="ok"),
        sa.Column("distance_override_km", sa.Numeric(7, 1)),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("raw_text", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.UniqueConstraint(
            "vehicle_id", "entry_type", "date", "odometer_km", name="uq_fuel_entry_dedupe"
        ),
    )

    op.create_table(
        "odometer_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False, index=True
        ),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False, index=True),
        sa.Column("end_date", sa.Date()),
        sa.Column("old_reading_at_change", sa.Numeric(7, 1)),
        sa.Column("new_reading_at_change", sa.Numeric(7, 1)),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )

    op.create_table(
        "entry_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "fuel_entry_id",
            sa.Integer(),
            sa.ForeignKey("fuel_entries.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("old_values", sa.JSON(), nullable=False),
        sa.Column("new_values", sa.JSON(), nullable=False),
        sa.Column(
            "changed_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_table("entry_audit")
    op.drop_table("odometer_events")
    op.drop_table("fuel_entries")
    op.drop_table("vehicles")
    op.drop_table("users")
