-- CRM and workplace schema for the TADF experiments (SQLite).
-- Mirrors the CRMArena Salesforce object model (Huang et al., 2025) for
-- accounts, contacts, agents, cases, opportunities; emails and events follow
-- the WorkBench sandbox shape (Styles et al., 2024) used by archetype F.
-- Created by experiments/load_db.py.

DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS emails;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS cases;
DROP TABLE IF EXISTS opportunities;
DROP TABLE IF EXISTS agents;
DROP TABLE IF EXISTS accounts;

CREATE TABLE accounts (
    id       INTEGER PRIMARY KEY,
    name     TEXT,
    region   TEXT,
    industry TEXT,
    type     TEXT
);

CREATE TABLE contacts (
    id         INTEGER PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    name       TEXT,
    email      TEXT
);

CREATE TABLE agents (
    id     INTEGER PRIMARY KEY,
    name   TEXT,
    team   TEXT,
    region TEXT,
    email  TEXT
);

CREATE TABLE cases (
    id             INTEGER PRIMARY KEY,
    account_id     INTEGER REFERENCES accounts(id),
    agent_id       INTEGER REFERENCES agents(id),
    subject        TEXT,
    issue_category TEXT,
    status         TEXT,
    priority       TEXT,
    created_at     TEXT,
    closed_at      TEXT,
    transfer_count INTEGER
);

CREATE TABLE opportunities (
    id             INTEGER PRIMARY KEY,
    account_id     INTEGER REFERENCES accounts(id),
    owner_agent_id INTEGER REFERENCES agents(id),
    name           TEXT,
    amount         REAL,
    stage          TEXT,
    created_at     TEXT,
    close_date     TEXT,
    is_won         INTEGER
);

-- WorkBench-style mail mailbox. Status: inbox | outbox | deleted.
CREATE TABLE emails (
    id        INTEGER PRIMARY KEY,
    sender    TEXT,
    recipient TEXT,
    subject   TEXT,
    body      TEXT,
    sent_at   TEXT,
    status    TEXT DEFAULT 'inbox'
);

-- WorkBench-style calendar. Status: confirmed | deleted | tentative.
-- attendees is a comma-separated list of email addresses.
CREATE TABLE events (
    id              INTEGER PRIMARY KEY,
    name            TEXT,
    organizer_email TEXT,
    attendees       TEXT,
    start_time      TEXT,
    end_time        TEXT,
    status          TEXT DEFAULT 'confirmed'
);
