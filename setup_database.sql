-- FarmGuard Database Setup Script for PostgreSQL
-- Target Database: livestock

-- Run manually in psql or via python initialization:
-- CREATE DATABASE livestock;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    status VARCHAR(30) DEFAULT 'APPROVED',
    address TEXT,
    farm_name VARCHAR(150),
    cattle_count INTEGER DEFAULT 0,
    buffalo_count INTEGER DEFAULT 0,
    goat_count INTEGER DEFAULT 0,
    sheep_count INTEGER DEFAULT 0,
    poultry_count INTEGER DEFAULT 0,
    other_livestock TEXT,
    vet_reg_number VARCHAR(100),
    qualification VARCHAR(150),
    vet_council_details TEXT,
    verification_doc_path VARCHAR(255),
    verification_doc_filename VARCHAR(255),
    rejection_reason TEXT,
    correction_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS animals (
    id SERIAL PRIMARY KEY,
    tag_number VARCHAR(50) UNIQUE NOT NULL,
    species VARCHAR(50) NOT NULL,
    farmer_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS drugs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    active_ingredient VARCHAR(100),
    species VARCHAR(150),
    route VARCHAR(150),
    indication TEXT,
    withdrawal_period_days INTEGER NOT NULL,
    max_dosage FLOAT,
    unit VARCHAR(20),
    source VARCHAR(255),
    source_date VARCHAR(50),
    mrl_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS amu_entries (
    id SERIAL PRIMARY KEY,
    entry_id VARCHAR(50) UNIQUE NOT NULL,
    farmer_id INTEGER REFERENCES users(id),
    animal_id INTEGER REFERENCES animals(id),
    drug_id INTEGER REFERENCES drugs(id),
    dosage FLOAT NOT NULL,
    unit VARCHAR(20) NOT NULL,
    route VARCHAR(100),
    indication TEXT,
    treatment_date DATE NOT NULL,
    withdrawal_end_date DATE,
    expected_selling_date DATE,
    status VARCHAR(20) DEFAULT 'pending',
    vet_id INTEGER REFERENCES users(id),
    vet_notes TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    log_id VARCHAR(50) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    related_entry_id VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    alert_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rag_evidences (
    id SERIAL PRIMARY KEY,
    amu_entry_id INTEGER REFERENCES amu_entries(id) ON DELETE CASCADE,
    document_title VARCHAR(255) NOT NULL,
    retrieved_chunk TEXT NOT NULL,
    source_reference VARCHAR(255) NOT NULL,
    recommended_withdrawal_days INTEGER,
    max_allowed_dosage FLOAT,
    mrl_info TEXT,
    regulatory_summary TEXT,
    verification_status VARCHAR(50),
    verification_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_amu_entries_farmer ON amu_entries(farmer_id);
CREATE INDEX IF NOT EXISTS idx_amu_entries_status ON amu_entries(status);
CREATE INDEX IF NOT EXISTS idx_amu_entries_withdrawal ON amu_entries(withdrawal_end_date);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_rag_evidences_entry ON rag_evidences(amu_entry_id);

