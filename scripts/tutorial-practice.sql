-- Seed state for the tutorial lessons that change data.
--
-- Those lessons must not write into sakila, because every reading lesson
-- describes what sakila holds. They use this database instead, and each one
-- starts from the state this file creates. scripts/verify-tutorial-examples.py
-- loads it before a lesson that carries {/* verify-reset */}, so a lesson's
-- pasted output stays reproducible however many times the check runs.
--
-- The same block appears in tutorial/insert.mdx, which is where a reader gets
-- it. Keep the two in step.

DROP DATABASE IF EXISTS sakila_practice;
CREATE DATABASE sakila_practice;
USE sakila_practice;

CREATE TABLE member (
  member_id  INT UNSIGNED NOT NULL AUTO_INCREMENT,
  first_name VARCHAR(45) NOT NULL,
  last_name  VARCHAR(45) NOT NULL,
  email      VARCHAR(100) DEFAULT NULL,
  joined     DATE NOT NULL,
  active     TINYINT NOT NULL DEFAULT 1,
  PRIMARY KEY (member_id),
  UNIQUE KEY uq_member_email (email)
);

INSERT INTO member (first_name, last_name, email, joined, active) VALUES
  ('Mary',     'Smith',    'mary.smith@example.com',       '2026-01-04', 1),
  ('Patricia', 'Johnson',  'patricia.johnson@example.com', '2026-02-11', 1),
  ('Linda',    'Williams', 'linda.williams@example.com',   '2026-03-02', 0);

CREATE TABLE rating_count (
  rating VARCHAR(10) NOT NULL,
  films  INT UNSIGNED NOT NULL,
  PRIMARY KEY (rating)
);

CREATE TABLE account (
  account_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  owner      VARCHAR(45) NOT NULL,
  balance    DECIMAL(10,2) NOT NULL,
  PRIMARY KEY (account_id)
);

INSERT INTO account (owner, balance) VALUES
  ('Mary Smith',       500.00),
  ('Patricia Johnson', 250.00);
