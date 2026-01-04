-- ============================================================
-- INTELLIGENT PLACEMENT PLATFORM - DATABASE SCHEMA
-- ============================================================
-- Database: PostgreSQL
-- Purpose: Store all structured, normalized, transactional data
-- 
-- NORMALIZATION: All tables are in 3NF (Third Normal Form)
-- - No repeating groups (1NF)
-- - No partial dependencies (2NF)  
-- - No transitive dependencies (3NF)
-- ============================================================

-- ============================================================
-- CLEANUP: Drop existing tables (for fresh setup)
-- Order matters due to foreign key constraints
-- ============================================================

DROP VIEW IF EXISTS vw_student_application_summary CASCADE;
DROP VIEW IF EXISTS vw_company_hiring_stats CASCADE;
DROP VIEW IF EXISTS vw_skill_demand_analysis CASCADE;

DROP TABLE IF EXISTS ai_recommendations CASCADE;
DROP TABLE IF EXISTS student_skills CASCADE;
DROP TABLE IF EXISTS job_required_skills CASCADE;
DROP TABLE IF EXISTS skills CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================================
-- TABLE: users
-- Purpose: Authentication and authorization
-- Why separate? Single Responsibility - auth is separate from profile
-- ============================================================

CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('student', 'company', 'admin')),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS 'Authentication table - stores login credentials and roles';
COMMENT ON COLUMN users.role IS 'User type: student, company, or admin';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hashed password - never store plaintext!';

-- ============================================================
-- TABLE: students
-- Purpose: Student profile information
-- FK: user_id references users (1:1 relationship)
-- ============================================================

CREATE TABLE students (
    student_id      SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    full_name       VARCHAR(100) NOT NULL,
    phone           VARCHAR(20),
    university      VARCHAR(200),
    degree          VARCHAR(100),
    major           VARCHAR(100),
    graduation_year INTEGER CHECK (graduation_year >= 2000 AND graduation_year <= 2100),
    cgpa            DECIMAL(3,2) CHECK (cgpa >= 0 AND cgpa <= 10),
    resume_mongo_id VARCHAR(50),  -- Reference to MongoDB document
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE students IS 'Student profiles with academic information';
COMMENT ON COLUMN students.resume_mongo_id IS 'MongoDB ObjectId reference to parsed resume document';
COMMENT ON COLUMN students.cgpa IS 'CGPA on 10-point scale';

-- Index for faster lookups
CREATE INDEX idx_students_university ON students(university);
CREATE INDEX idx_students_graduation_year ON students(graduation_year);

-- ============================================================
-- TABLE: companies
-- Purpose: Company/employer profiles
-- FK: user_id references users (1:1 relationship)
-- ============================================================

CREATE TABLE companies (
    company_id      SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    company_name    VARCHAR(200) NOT NULL,
    industry        VARCHAR(100),
    company_size    VARCHAR(50) CHECK (company_size IN ('startup', 'small', 'medium', 'large', 'enterprise')),
    website         VARCHAR(255),
    description     TEXT,
    headquarters    VARCHAR(200),
    founded_year    INTEGER CHECK (founded_year >= 1800 AND founded_year <= 2100),
    is_verified     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE companies IS 'Company profiles for employers posting jobs';
COMMENT ON COLUMN companies.is_verified IS 'Admin-verified legitimate company';
COMMENT ON COLUMN companies.company_size IS 'Company size category for filtering';

-- Index for searching companies
CREATE INDEX idx_companies_industry ON companies(industry);
CREATE INDEX idx_companies_name ON companies(company_name);

-- ============================================================
-- TABLE: jobs
-- Purpose: Job postings by companies
-- FK: company_id references companies
-- ============================================================

CREATE TABLE jobs (
    job_id              SERIAL PRIMARY KEY,
    company_id          INTEGER NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    title               VARCHAR(200) NOT NULL,
    description         TEXT,
    job_type            VARCHAR(50) CHECK (job_type IN ('full-time', 'part-time', 'internship', 'contract')),
    location            VARCHAR(200),
    is_remote           BOOLEAN DEFAULT FALSE,
    min_experience      INTEGER DEFAULT 0 CHECK (min_experience >= 0),
    max_experience      INTEGER CHECK (max_experience >= 0),
    min_salary          DECIMAL(12,2),
    max_salary          DECIMAL(12,2),
    currency            VARCHAR(3) DEFAULT 'INR',
    openings            INTEGER DEFAULT 1 CHECK (openings > 0),
    application_deadline DATE,
    status              VARCHAR(20) DEFAULT 'open' CHECK (status IN ('draft', 'open', 'closed', 'filled')),
    jd_mongo_id         VARCHAR(50),  -- Reference to MongoDB parsed JD
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraint: max_experience should be >= min_experience
    CONSTRAINT chk_experience_range CHECK (max_experience IS NULL OR max_experience >= min_experience),
    -- Constraint: max_salary should be >= min_salary
    CONSTRAINT chk_salary_range CHECK (max_salary IS NULL OR min_salary IS NULL OR max_salary >= min_salary)
);

COMMENT ON TABLE jobs IS 'Job postings created by companies';
COMMENT ON COLUMN jobs.jd_mongo_id IS 'MongoDB ObjectId reference to parsed job description';
COMMENT ON COLUMN jobs.status IS 'Job status: draft (not visible), open (accepting), closed (not accepting), filled';

-- Indexes for job searching
CREATE INDEX idx_jobs_company ON jobs(company_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_type ON jobs(job_type);
CREATE INDEX idx_jobs_location ON jobs(location);
CREATE INDEX idx_jobs_deadline ON jobs(application_deadline);

-- ============================================================
-- TABLE: skills
-- Purpose: Master list of normalized skills
-- Why separate table? Avoid data duplication, enable skill analytics
-- ============================================================

CREATE TABLE skills (
    skill_id        SERIAL PRIMARY KEY,
    skill_name      VARCHAR(100) NOT NULL UNIQUE,
    category        VARCHAR(50),  -- e.g., 'programming', 'database', 'soft-skill'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE skills IS 'Master skill dictionary - normalized skill names';
COMMENT ON COLUMN skills.category IS 'Skill category for grouping and analysis';

-- Index for skill lookups
CREATE INDEX idx_skills_name ON skills(skill_name);
CREATE INDEX idx_skills_category ON skills(category);

-- ============================================================
-- TABLE: student_skills (Junction Table)
-- Purpose: Many-to-many relationship between students and skills
-- This is a proper junction table (associative entity)
-- ============================================================

CREATE TABLE student_skills (
    student_skill_id    SERIAL PRIMARY KEY,
    student_id          INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    skill_id            INTEGER NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    proficiency_level   VARCHAR(20) CHECK (proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    years_experience    DECIMAL(3,1) CHECK (years_experience >= 0),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Prevent duplicate skill entries for same student
    UNIQUE(student_id, skill_id)
);

COMMENT ON TABLE student_skills IS 'Junction table: links students to their skills (M:N)';
COMMENT ON COLUMN student_skills.proficiency_level IS 'Self-reported skill proficiency';

-- Indexes for skill matching queries
CREATE INDEX idx_student_skills_student ON student_skills(student_id);
CREATE INDEX idx_student_skills_skill ON student_skills(skill_id);

-- ============================================================
-- TABLE: job_required_skills (Junction Table)
-- Purpose: Many-to-many relationship between jobs and required skills
-- ============================================================

CREATE TABLE job_required_skills (
    job_skill_id        SERIAL PRIMARY KEY,
    job_id              INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    skill_id            INTEGER NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    is_mandatory        BOOLEAN DEFAULT TRUE,  -- Required vs preferred
    min_proficiency     VARCHAR(20) CHECK (min_proficiency IN ('beginner', 'intermediate', 'advanced', 'expert')),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Prevent duplicate skill entries for same job
    UNIQUE(job_id, skill_id)
);

COMMENT ON TABLE job_required_skills IS 'Junction table: links jobs to required skills (M:N)';
COMMENT ON COLUMN job_required_skills.is_mandatory IS 'TRUE = required skill, FALSE = nice-to-have';

-- Indexes for job-skill matching
CREATE INDEX idx_job_skills_job ON job_required_skills(job_id);
CREATE INDEX idx_job_skills_skill ON job_required_skills(skill_id);

-- ============================================================
-- TABLE: applications
-- Purpose: Track job applications by students
-- FK: student_id, job_id (represents the application relationship)
-- ============================================================

CREATE TABLE applications (
    application_id      SERIAL PRIMARY KEY,
    student_id          INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    job_id              INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    status              VARCHAR(30) DEFAULT 'applied' CHECK (status IN (
                            'applied',      -- Initial state
                            'under_review', -- Being reviewed by company
                            'shortlisted',  -- Shortlisted for interview
                            'interviewed',  -- Interview completed
                            'offered',      -- Job offer extended
                            'accepted',     -- Student accepted offer
                            'rejected',     -- Rejected by company
                            'withdrawn'     -- Withdrawn by student
                        )),
    cover_letter        TEXT,
    applied_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes               TEXT,  -- Internal notes by company
    
    -- Prevent multiple applications to same job
    UNIQUE(student_id, job_id)
);

COMMENT ON TABLE applications IS 'Job applications submitted by students';
COMMENT ON COLUMN applications.status IS 'Application lifecycle status';
COMMENT ON COLUMN applications.notes IS 'Private notes by hiring company';

-- Indexes for application queries
CREATE INDEX idx_applications_student ON applications(student_id);
CREATE INDEX idx_applications_job ON applications(job_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_date ON applications(applied_at);

-- ============================================================
-- TABLE: ai_recommendations
-- Purpose: Store AI-generated job recommendations for students
-- This is where AI OUTPUT gets stored in the RELATIONAL database
-- ============================================================

CREATE TABLE ai_recommendations (
    recommendation_id   SERIAL PRIMARY KEY,
    student_id          INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    job_id              INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    match_score         DECIMAL(5,4) CHECK (match_score >= 0 AND match_score <= 1),  -- 0.0000 to 1.0000
    skill_match_pct     DECIMAL(5,2) CHECK (skill_match_pct >= 0 AND skill_match_pct <= 100),
    experience_match    BOOLEAN,
    recommendation_reason TEXT,  -- AI-generated explanation
    is_viewed           BOOLEAN DEFAULT FALSE,
    is_applied          BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at          TIMESTAMP,  -- Recommendations can expire
    
    -- One recommendation per student-job pair
    UNIQUE(student_id, job_id)
);

COMMENT ON TABLE ai_recommendations IS 'AI-generated job recommendations stored in SQL';
COMMENT ON COLUMN ai_recommendations.match_score IS 'Cosine similarity score from embedding comparison (0-1)';
COMMENT ON COLUMN ai_recommendations.skill_match_pct IS 'Percentage of required skills matched';
COMMENT ON COLUMN ai_recommendations.recommendation_reason IS 'AI-generated explanation for the match';

-- Indexes for recommendation queries
CREATE INDEX idx_recommendations_student ON ai_recommendations(student_id);
CREATE INDEX idx_recommendations_job ON ai_recommendations(job_id);
CREATE INDEX idx_recommendations_score ON ai_recommendations(match_score DESC);

-- ============================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_students_updated_at BEFORE UPDATE ON students
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- INSERT: Seed some initial skills
-- These are common tech skills for placement platforms
-- ============================================================

INSERT INTO skills (skill_name, category) VALUES
    -- Programming Languages
    ('Python', 'programming'),
    ('Java', 'programming'),
    ('JavaScript', 'programming'),
    ('TypeScript', 'programming'),
    ('C++', 'programming'),
    ('C', 'programming'),
    ('Go', 'programming'),
    ('Rust', 'programming'),
    ('Ruby', 'programming'),
    ('PHP', 'programming'),
    
    -- Web Development
    ('React', 'web'),
    ('Angular', 'web'),
    ('Vue.js', 'web'),
    ('Node.js', 'web'),
    ('Django', 'web'),
    ('Flask', 'web'),
    ('FastAPI', 'web'),
    ('Spring Boot', 'web'),
    ('Express.js', 'web'),
    ('HTML/CSS', 'web'),
    
    -- Databases
    ('PostgreSQL', 'database'),
    ('MySQL', 'database'),
    ('MongoDB', 'database'),
    ('Redis', 'database'),
    ('Oracle', 'database'),
    ('SQL Server', 'database'),
    ('Cassandra', 'database'),
    ('Elasticsearch', 'database'),
    
    -- Cloud & DevOps
    ('AWS', 'cloud'),
    ('Azure', 'cloud'),
    ('GCP', 'cloud'),
    ('Docker', 'devops'),
    ('Kubernetes', 'devops'),
    ('Jenkins', 'devops'),
    ('Git', 'devops'),
    ('CI/CD', 'devops'),
    ('Terraform', 'devops'),
    
    -- Data Science & ML
    ('Machine Learning', 'data-science'),
    ('Deep Learning', 'data-science'),
    ('TensorFlow', 'data-science'),
    ('PyTorch', 'data-science'),
    ('Pandas', 'data-science'),
    ('NumPy', 'data-science'),
    ('Data Analysis', 'data-science'),
    ('NLP', 'data-science'),
    ('Computer Vision', 'data-science'),
    
    -- Soft Skills
    ('Communication', 'soft-skill'),
    ('Leadership', 'soft-skill'),
    ('Problem Solving', 'soft-skill'),
    ('Teamwork', 'soft-skill'),
    ('Time Management', 'soft-skill'),
    ('Critical Thinking', 'soft-skill')
ON CONFLICT (skill_name) DO NOTHING;

-- ============================================================
-- VERIFICATION QUERIES
-- Run these to verify schema is correct
-- ============================================================

-- Check all tables exist
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Check foreign key relationships
-- SELECT
--     tc.table_name, 
--     kcu.column_name,
--     ccu.table_name AS foreign_table_name,
--     ccu.column_name AS foreign_column_name
-- FROM information_schema.table_constraints AS tc
-- JOIN information_schema.key_column_usage AS kcu
--     ON tc.constraint_name = kcu.constraint_name
-- JOIN information_schema.constraint_column_usage AS ccu
--     ON ccu.constraint_name = tc.constraint_name
-- WHERE tc.constraint_type = 'FOREIGN KEY';

-- ============================================================
-- SCHEMA COMPLETE
-- ============================================================
-- ============================================================
-- VIEWS (Add these to the end of schema.sql)
-- ============================================================

-- ============================================================
-- VIEW 1: Student Application Summary
-- Purpose: Show each student's application statistics
-- Uses: JOIN, COUNT, GROUP BY
-- ============================================================

CREATE VIEW vw_student_application_summary AS
SELECT 
    s.student_id,
    s.full_name,
    s.university,
    s.cgpa,
    COUNT(a.application_id) AS total_applications,
    COUNT(CASE WHEN a.status = 'applied' THEN 1 END) AS pending_applications,
    COUNT(CASE WHEN a.status = 'shortlisted' THEN 1 END) AS shortlisted,
    COUNT(CASE WHEN a.status = 'offered' THEN 1 END) AS offers_received,
    COUNT(CASE WHEN a.status = 'accepted' THEN 1 END) AS offers_accepted,
    COUNT(CASE WHEN a.status = 'rejected' THEN 1 END) AS rejections,
    MAX(a.applied_at) AS last_application_date
FROM students s
LEFT JOIN applications a ON s.student_id = a.student_id
GROUP BY s.student_id, s.full_name, s.university, s.cgpa;

COMMENT ON VIEW vw_student_application_summary IS 
'Aggregated view of each student''s application status and statistics';

-- ============================================================
-- VIEW 2: Company Hiring Statistics
-- Purpose: Show recruitment metrics per company
-- Uses: Multiple JOINs, COUNT, AVG
-- ============================================================

CREATE VIEW vw_company_hiring_stats AS
SELECT 
    c.company_id,
    c.company_name,
    c.industry,
    COUNT(DISTINCT j.job_id) AS total_jobs_posted,
    COUNT(DISTINCT CASE WHEN j.status = 'open' THEN j.job_id END) AS active_jobs,
    COUNT(a.application_id) AS total_applications_received,
    COUNT(CASE WHEN a.status = 'shortlisted' THEN 1 END) AS total_shortlisted,
    COUNT(CASE WHEN a.status = 'offered' THEN 1 END) AS total_offers_made,
    COUNT(CASE WHEN a.status = 'accepted' THEN 1 END) AS total_hires,
    ROUND(AVG(j.min_salary), 2) AS avg_min_salary,
    ROUND(AVG(j.max_salary), 2) AS avg_max_salary
FROM companies c
LEFT JOIN jobs j ON c.company_id = j.company_id
LEFT JOIN applications a ON j.job_id = a.job_id
GROUP BY c.company_id, c.company_name, c.industry;

COMMENT ON VIEW vw_company_hiring_stats IS 
'Hiring metrics and statistics for each company';

-- ============================================================
-- VIEW 3: Skill Demand Analysis
-- Purpose: Analyze which skills are most in-demand
-- Uses: Complex JOINs, COUNT, aggregation
-- ============================================================

CREATE VIEW vw_skill_demand_analysis AS
SELECT 
    sk.skill_id,
    sk.skill_name,
    sk.category,
    COUNT(DISTINCT jrs.job_id) AS jobs_requiring_skill,
    COUNT(DISTINCT CASE WHEN jrs.is_mandatory = TRUE THEN jrs.job_id END) AS jobs_mandatory,
    COUNT(DISTINCT ss.student_id) AS students_with_skill,
    COUNT(DISTINCT CASE WHEN ss.proficiency_level IN ('advanced', 'expert') THEN ss.student_id END) AS advanced_students,
    ROUND(
        COUNT(DISTINCT ss.student_id)::NUMERIC / 
        NULLIF(COUNT(DISTINCT jrs.job_id), 0), 
        2
    ) AS supply_demand_ratio
FROM skills sk
LEFT JOIN job_required_skills jrs ON sk.skill_id = jrs.skill_id
LEFT JOIN student_skills ss ON sk.skill_id = ss.skill_id
GROUP BY sk.skill_id, sk.skill_name, sk.category
ORDER BY jobs_requiring_skill DESC;

COMMENT ON VIEW vw_skill_demand_analysis IS 
'Market analysis of skill demand vs supply in the platform';