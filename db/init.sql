-- ============================================================================
-- Script d'initialisation de la base de données MyPacer (DEV LOCAL)
-- ============================================================================
-- ⚠️ COPIE LOCALE POUR DÉVELOPPEMENT AUTONOME
--
-- Source de vérité : mypacer_infra/init-db/01-init-schema.sql
-- En cas de divergence, le schéma de l'infra fait foi.
--
-- Ce script est utilisé UNIQUEMENT pour le développement local de l'API
-- via docker-compose.dev.yml. En production/staging, c'est l'infra qui
-- gère l'initialisation de la base de données.
-- ============================================================================

\echo '========================================'
\echo 'Initializing MyPacer Database Schema (DEV)'
\echo '========================================'

-- Extensions nécessaires
\echo 'Creating PostgreSQL extensions...'
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- Pour recherche floue
CREATE EXTENSION IF NOT EXISTS unaccent;     -- Pour normalisation sans accents

-- ============================================================================
-- Table: clubs
-- ============================================================================
\echo 'Creating clubs table...'
CREATE TABLE IF NOT EXISTS clubs (
    id SERIAL PRIMARY KEY,
    ffa_id TEXT NOT NULL UNIQUE,              -- ID FFA du club
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,            -- Nom normalisé (minuscules, sans accents)
    first_year INTEGER,                       -- Première année d'activité connue
    last_year INTEGER,                        -- Dernière année d'activité connue
    url TEXT,                                 -- URL de la page du club
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index pour recherche rapide sur clubs
CREATE INDEX IF NOT EXISTS idx_clubs_ffa_id ON clubs(ffa_id);
CREATE INDEX IF NOT EXISTS idx_clubs_normalized_name_trgm ON clubs
    USING GIN (normalized_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_clubs_years ON clubs(first_year, last_year);

-- ============================================================================
-- Table: athletes
-- ============================================================================
\echo 'Creating athletes table...'
CREATE TABLE IF NOT EXISTS athletes (
    id SERIAL PRIMARY KEY,
    ffa_id TEXT NOT NULL UNIQUE,              -- ID FFA de l'athlète (ancien ou nouveau)
    license_id TEXT,                          -- Numéro de licence (identifiant métier)
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,            -- Nom normalisé pour recherche
    url TEXT,                                 -- URL de la page de l'athlète
    birth_date TEXT,                          -- Année de naissance
    sexe TEXT,                                -- M/F
    nationality TEXT,                         -- Code pays (FRA, etc.)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index pour recherche rapide sur athletes
CREATE INDEX IF NOT EXISTS idx_athletes_ffa_id ON athletes(ffa_id);

-- Index unique partiel sur license_id (uniquement pour les valeurs valides)
-- Cela garantit qu'un license_id valide ne peut exister qu'une fois
CREATE UNIQUE INDEX IF NOT EXISTS idx_athletes_license_id_unique ON athletes(license_id)
    WHERE license_id IS NOT NULL
      AND license_id != ''
      AND license_id != '-'
      AND license_id != 'None';

-- Index non-unique pour recherche par license_id (inclut toutes les valeurs)
CREATE INDEX IF NOT EXISTS idx_athletes_license_id ON athletes(license_id)
    WHERE license_id IS NOT NULL AND license_id != '' AND license_id != '-' AND license_id != 'None';
CREATE INDEX IF NOT EXISTS idx_athletes_normalized_name_trgm ON athletes
    USING GIN (normalized_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_athletes_normalized_name ON athletes(normalized_name);
-- Recherche par préfixe (LIKE 'mar%' + ORDER BY ... USING ~<~) côté API
CREATE INDEX IF NOT EXISTS idx_athletes_normalized_name_prefix ON athletes(normalized_name text_pattern_ops);
CREATE INDEX IF NOT EXISTS idx_athletes_sexe ON athletes(sexe) WHERE sexe IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_athletes_birth_date ON athletes(birth_date) WHERE birth_date IS NOT NULL;

-- ============================================================================
-- Fonction: Normaliser un texte (minuscules, sans accents, espaces nettoyés)
-- ============================================================================
\echo 'Creating normalization function...'
CREATE OR REPLACE FUNCTION normalize_text(text) RETURNS TEXT AS $$
    SELECT lower(unaccent(regexp_replace($1, '\s+', ' ', 'g')))
$$ LANGUAGE SQL IMMUTABLE;

-- ============================================================================
-- Triggers: Mise à jour automatique de normalized_name et updated_at
-- ============================================================================
\echo 'Creating triggers...'

-- Trigger pour athletes
CREATE OR REPLACE FUNCTION update_athlete_normalized_name()
RETURNS TRIGGER AS $$
BEGIN
    NEW.normalized_name := normalize_text(NEW.name);
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_athlete_normalized_name ON athletes;
CREATE TRIGGER trigger_update_athlete_normalized_name
    BEFORE INSERT OR UPDATE ON athletes
    FOR EACH ROW
    EXECUTE FUNCTION update_athlete_normalized_name();

-- Trigger pour clubs
CREATE OR REPLACE FUNCTION update_club_normalized_name()
RETURNS TRIGGER AS $$
BEGIN
    NEW.normalized_name := normalize_text(NEW.name);
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_club_normalized_name ON clubs;
CREATE TRIGGER trigger_update_club_normalized_name
    BEFORE INSERT OR UPDATE ON clubs
    FOR EACH ROW
    EXECUTE FUNCTION update_club_normalized_name();

-- ============================================================================
-- Vues utiles
-- ============================================================================
\echo 'Creating views...'

-- Vue des statistiques athletes
CREATE OR REPLACE VIEW v_athletes_stats AS
SELECT
    COUNT(*) as total_athletes,
    COUNT(DISTINCT license_id) FILTER (WHERE license_id IS NOT NULL AND license_id != '' AND license_id != '-' AND license_id != 'None') as athletes_with_valid_license,
    COUNT(*) FILTER (WHERE license_id IS NULL OR license_id = '' OR license_id = '-' OR license_id = 'None') as athletes_without_license,
    COUNT(DISTINCT sexe) FILTER (WHERE sexe IS NOT NULL) as distinct_sexes,
    COUNT(*) FILTER (WHERE sexe = 'M') as male_count,
    COUNT(*) FILTER (WHERE sexe = 'F') as female_count,
    MIN(birth_date::INTEGER) FILTER (WHERE birth_date ~ '^\d{4}$') as oldest_birth_year,
    MAX(birth_date::INTEGER) FILTER (WHERE birth_date ~ '^\d{4}$') as youngest_birth_year
FROM athletes;

-- Vue des statistiques clubs
CREATE OR REPLACE VIEW v_clubs_stats AS
SELECT
    COUNT(*) as total_clubs,
    MIN(first_year) as earliest_year,
    MAX(last_year) as latest_year,
    AVG(last_year - first_year + 1) FILTER (WHERE first_year IS NOT NULL AND last_year IS NOT NULL) as avg_years_active
FROM clubs;

COMMENT ON VIEW v_athletes_stats IS 'Statistiques globales sur les athlètes';
COMMENT ON VIEW v_clubs_stats IS 'Statistiques globales sur les clubs';

\echo '========================================'
\echo 'MyPacer Database Schema Created Successfully! (DEV)'
\echo '========================================'
