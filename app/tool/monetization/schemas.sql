-- Monetization Tools Database Schemas
-- PostgreSQL Compatible
-- Created: 2025-01-01

-- ============================================================================
-- 1. MARKETPLACE ARBITRAGE TOOL SCHEMAS
-- ============================================================================

-- Main products table for arbitrage opportunities
CREATE TABLE IF NOT EXISTS arbitrage_products (
    id SERIAL PRIMARY KEY,
    source_platform VARCHAR(50) NOT NULL,
    source_url TEXT NOT NULL,
    source_price DECIMAL(10,2) NOT NULL,
    source_product_id VARCHAR(200),
    target_platform VARCHAR(50) NOT NULL,
    target_price DECIMAL(10,2),
    target_url TEXT,
    product_title TEXT NOT NULL,
    product_description TEXT,
    category VARCHAR(100),
    subcategory VARCHAR(100),

    -- Pricing & profitability
    estimated_fees DECIMAL(10,2) DEFAULT 0,
    shipping_cost DECIMAL(10,2) DEFAULT 0,
    estimated_profit DECIMAL(10,2),
    profit_margin DECIMAL(5,2),
    roi_percentage DECIMAL(5,2),

    -- Product quality metrics
    rating DECIMAL(3,2),
    review_count INT DEFAULT 0,
    seller_rating DECIMAL(3,2),
    shipping_time_days INT,

    -- Status tracking
    status VARCHAR(20) DEFAULT 'discovered', -- discovered, listed, sold, expired
    listing_created_at TIMESTAMP,
    sold_at TIMESTAMP,

    -- Metadata
    last_checked TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Price history for tracking
CREATE TABLE IF NOT EXISTS arbitrage_price_history (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES arbitrage_products(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    in_stock BOOLEAN DEFAULT TRUE,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- Listings created for products
CREATE TABLE IF NOT EXISTS arbitrage_listings (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES arbitrage_products(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    listing_id VARCHAR(200),
    listing_url TEXT,
    listing_price DECIMAL(10,2) NOT NULL,
    quantity INT DEFAULT 1,
    status VARCHAR(20) DEFAULT 'active', -- active, sold, cancelled
    views INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    sold_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_arbitrage_profit ON arbitrage_products(profit_margin DESC, status);
CREATE INDEX IF NOT EXISTS idx_arbitrage_platform ON arbitrage_products(source_platform, target_platform);
CREATE INDEX IF NOT EXISTS idx_arbitrage_status ON arbitrage_products(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_product ON arbitrage_price_history(product_id, recorded_at DESC);

-- ============================================================================
-- 2. DATA COLLECTION SERVICE TOOL SCHEMAS
-- ============================================================================

-- Data collection jobs configuration
CREATE TABLE IF NOT EXISTS data_collection_jobs (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50),
    job_name VARCHAR(200) NOT NULL,
    job_type VARCHAR(50) NOT NULL, -- lead_generation, price_monitoring, market_research, contact_scraping
    target_sources TEXT[] NOT NULL,
    data_schema JSONB NOT NULL,

    -- Collection settings
    collection_frequency VARCHAR(20) DEFAULT 'once', -- once, hourly, daily, weekly
    last_run TIMESTAMP,
    next_run TIMESTAMP,

    -- Statistics
    records_collected INT DEFAULT 0,
    records_validated INT DEFAULT 0,
    records_exported INT DEFAULT 0,

    -- Status
    status VARCHAR(20) DEFAULT 'active', -- active, paused, completed, failed
    error_message TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Collected data storage
CREATE TABLE IF NOT EXISTS collected_data (
    id SERIAL PRIMARY KEY,
    job_id INT REFERENCES data_collection_jobs(id) ON DELETE CASCADE,
    raw_data JSONB NOT NULL,
    cleaned_data JSONB,
    quality_score DECIMAL(3,2) DEFAULT 0,
    validation_errors JSONB,

    -- Export tracking
    exported BOOLEAN DEFAULT FALSE,
    export_format VARCHAR(20),
    exported_at TIMESTAMP,

    -- Metadata
    collected_at TIMESTAMP DEFAULT NOW(),
    source_url TEXT
);

-- Client configuration
CREATE TABLE IF NOT EXISTS data_service_clients (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) UNIQUE NOT NULL,
    client_name VARCHAR(200) NOT NULL,
    api_key VARCHAR(200),
    webhook_url TEXT,
    email_notifications BOOLEAN DEFAULT TRUE,
    contact_email VARCHAR(200),

    -- Subscription
    subscription_tier VARCHAR(50) DEFAULT 'basic',
    monthly_quota INT DEFAULT 1000,
    records_used_this_month INT DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_status ON data_collection_jobs(status, next_run);
CREATE INDEX IF NOT EXISTS idx_jobs_client ON data_collection_jobs(client_id);
CREATE INDEX IF NOT EXISTS idx_collected_data_job ON collected_data(job_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_collected_data_exported ON collected_data(exported, job_id);

-- ============================================================================
-- 3. LEAD GENERATION ENGINE TOOL SCHEMAS
-- ============================================================================

-- Main leads table
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(200),
    contact_name VARCHAR(200),
    job_title VARCHAR(100),
    seniority_level VARCHAR(50),

    -- Contact information
    email VARCHAR(200),
    email_verified BOOLEAN DEFAULT FALSE,
    phone VARCHAR(50),
    phone_verified BOOLEAN DEFAULT FALSE,
    linkedin_url TEXT,
    twitter_handle VARCHAR(100),

    -- Company information
    company_website TEXT,
    company_linkedin TEXT,
    industry VARCHAR(100),
    company_size VARCHAR(50),
    employee_count_min INT,
    employee_count_max INT,
    location VARCHAR(200),
    country VARCHAR(100),

    -- Technology & signals
    technologies_used TEXT[],
    tech_stack JSONB,
    growth_signals TEXT[],

    -- Scoring & qualification
    lead_score INT DEFAULT 0,
    qualification_status VARCHAR(20) DEFAULT 'new', -- new, qualified, contacted, converted, rejected
    rejection_reason TEXT,

    -- Discovery & enrichment
    discovery_source VARCHAR(100),
    discovery_method VARCHAR(100),
    discovered_at TIMESTAMP DEFAULT NOW(),
    last_enriched TIMESTAMP,
    enrichment_attempts INT DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Lead sources tracking
CREATE TABLE IF NOT EXISTS lead_sources (
    id SERIAL PRIMARY KEY,
    lead_id INT REFERENCES leads(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- linkedin, company_website, directory, database
    source_url TEXT,
    confidence_score DECIMAL(3,2) DEFAULT 0,
    data_found JSONB,
    discovered_at TIMESTAMP DEFAULT NOW()
);

-- Enrichment log
CREATE TABLE IF NOT EXISTS lead_enrichment_log (
    id SERIAL PRIMARY KEY,
    lead_id INT REFERENCES leads(id) ON DELETE CASCADE,
    enrichment_type VARCHAR(50) NOT NULL, -- email, phone, linkedin, company_data
    status VARCHAR(20) NOT NULL, -- success, failed, partial
    fields_added TEXT[],
    error_message TEXT,
    enriched_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(lead_score DESC, qualification_status);
CREATE INDEX IF NOT EXISTS idx_leads_company ON leads(company_name, industry);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_lead_sources_lead ON lead_sources(lead_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_log_lead ON lead_enrichment_log(lead_id, enriched_at DESC);

-- ============================================================================
-- 4. FREELANCE BID AUTOMATOR TOOL SCHEMAS
-- ============================================================================

-- Freelance projects discovered
CREATE TABLE IF NOT EXISTS freelance_projects (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL, -- upwork, fiverr, freelancer
    project_id VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,

    -- Budget information
    budget_min DECIMAL(10,2),
    budget_max DECIMAL(10,2),
    budget_type VARCHAR(20), -- fixed, hourly
    estimated_hours INT,

    -- Client information
    client_id VARCHAR(100),
    client_name VARCHAR(200),
    client_rating DECIMAL(3,2),
    client_spend_total DECIMAL(10,2),
    client_reviews_count INT DEFAULT 0,
    client_hire_rate DECIMAL(3,2),
    client_location VARCHAR(100),
    client_payment_verified BOOLEAN DEFAULT FALSE,

    -- Project details
    skills_required TEXT[],
    experience_level VARCHAR(50), -- entry, intermediate, expert
    project_length VARCHAR(50), -- short, medium, long
    proposals_count INT DEFAULT 0,
    posted_at TIMESTAMP,
    deadline TIMESTAMP,

    -- Quality scoring
    quality_score INT DEFAULT 0, -- 0-100
    scope_clarity_score INT,
    client_quality_score INT,
    competition_score INT,
    profitability_score INT,

    -- Status
    bid_submitted BOOLEAN DEFAULT FALSE,
    won BOOLEAN DEFAULT FALSE,
    project_url TEXT,

    -- Metadata
    discovered_at TIMESTAMP DEFAULT NOW(),
    analyzed_at TIMESTAMP
);

-- Bid proposals generated and submitted
CREATE TABLE IF NOT EXISTS bid_proposals (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES freelance_projects(id) ON DELETE CASCADE,
    proposal_text TEXT NOT NULL,
    bid_amount DECIMAL(10,2) NOT NULL,
    estimated_hours INT,
    delivery_days INT,

    -- Proposal strategy
    bid_strategy VARCHAR(50), -- competitive, premium, balanced
    customization_level VARCHAR(50), -- low, medium, high

    -- Outcome
    submitted_at TIMESTAMP,
    submission_status VARCHAR(20) DEFAULT 'draft', -- draft, submitted, accepted, rejected
    client_response VARCHAR(20), -- invited, shortlisted, hired, declined, no_response
    client_response_time_hours INT,
    won BOOLEAN DEFAULT FALSE,
    contract_value DECIMAL(10,2),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bidding results tracking
CREATE TABLE IF NOT EXISTS bidding_results (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    projects_scanned INT DEFAULT 0,
    proposals_submitted INT DEFAULT 0,
    invitations_received INT DEFAULT 0,
    contracts_won INT DEFAULT 0,
    total_revenue DECIMAL(10,2) DEFAULT 0,
    win_rate DECIMAL(5,2),
    avg_bid_amount DECIMAL(10,2)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_projects_quality ON freelance_projects(platform, quality_score DESC, posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_bid_status ON freelance_projects(bid_submitted, won);
CREATE INDEX IF NOT EXISTS idx_proposals_project ON bid_proposals(project_id);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON bid_proposals(submission_status, won);
CREATE INDEX IF NOT EXISTS idx_results_date ON bidding_results(date DESC, platform);

-- ============================================================================
-- 5. DOMAIN FLIP FINDER TOOL SCHEMAS
-- ============================================================================

-- Expired domains discovered
CREATE TABLE IF NOT EXISTS expired_domains (
    id SERIAL PRIMARY KEY,
    domain_name VARCHAR(255) UNIQUE NOT NULL,
    tld VARCHAR(20) NOT NULL, -- .com, .net, .io, etc

    -- Domain status
    status VARCHAR(20) DEFAULT 'available', -- available, registered, pending, auction
    expiry_date DATE,
    days_until_available INT,
    registrar VARCHAR(100),

    -- Traffic & SEO metrics
    previous_traffic_estimate INT DEFAULT 0,
    backlink_count INT DEFAULT 0,
    referring_domains INT DEFAULT 0,
    domain_authority INT DEFAULT 0,
    page_authority INT DEFAULT 0,
    spam_score INT DEFAULT 0,

    -- Archive & history
    archive_snapshots INT DEFAULT 0,
    first_archived DATE,
    last_archived DATE,
    previous_use_category VARCHAR(100),

    -- Valuation
    estimated_value DECIMAL(10,2),
    registration_cost DECIMAL(10,2) DEFAULT 10.00,
    potential_profit DECIMAL(10,2),
    valuation_method VARCHAR(50),

    -- Categorization
    categories TEXT[],
    keywords TEXT[],
    brandability_score INT DEFAULT 0,
    length INT,
    contains_numbers BOOLEAN DEFAULT FALSE,
    contains_hyphens BOOLEAN DEFAULT FALSE,

    -- Monetization potential
    monetization_methods TEXT[],
    revenue_estimate_monthly DECIMAL(10,2),

    -- Action tracking
    action_taken VARCHAR(50), -- none, watch_list, registered, sold
    registered_at TIMESTAMP,
    sold_at TIMESTAMP,
    sold_price DECIMAL(10,2),

    -- Metadata
    discovered_at TIMESTAMP DEFAULT NOW(),
    analyzed_at TIMESTAMP,
    last_checked TIMESTAMP DEFAULT NOW()
);

-- Domain metrics history
CREATE TABLE IF NOT EXISTS domain_metrics (
    id SERIAL PRIMARY KEY,
    domain_id INT REFERENCES expired_domains(id) ON DELETE CASCADE,
    metric_type VARCHAR(50) NOT NULL, -- da, pa, backlinks, traffic
    metric_value DECIMAL(10,2) NOT NULL,
    measured_at TIMESTAMP DEFAULT NOW()
);

-- Domain registrations tracked
CREATE TABLE IF NOT EXISTS domain_registrations (
    id SERIAL PRIMARY KEY,
    domain_id INT REFERENCES expired_domains(id),
    domain_name VARCHAR(255) NOT NULL,
    registrar VARCHAR(100),
    registration_cost DECIMAL(10,2),
    renewal_date DATE,
    auto_renew BOOLEAN DEFAULT TRUE,
    registered_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_domains_profit ON expired_domains(potential_profit DESC, status);
CREATE INDEX IF NOT EXISTS idx_domains_tld ON expired_domains(tld, status);
CREATE INDEX IF NOT EXISTS idx_domains_status ON expired_domains(status, discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_domains_da ON expired_domains(domain_authority DESC) WHERE domain_authority > 0;
CREATE INDEX IF NOT EXISTS idx_metrics_domain ON domain_metrics(domain_id, measured_at DESC);

-- ============================================================================
-- 6. CLIENT PROSPECTOR TOOL SCHEMAS
-- ============================================================================

-- Prospect companies
CREATE TABLE IF NOT EXISTS prospect_companies (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(200) NOT NULL,
    website TEXT,
    company_linkedin TEXT,

    -- Company details
    industry VARCHAR(100),
    sub_industry VARCHAR(100),
    description TEXT,
    employee_count INT,
    employee_count_range VARCHAR(50), -- 1-10, 11-50, 51-200, etc
    revenue_estimate DECIMAL(15,2),
    revenue_range VARCHAR(50),

    -- Location
    hq_location VARCHAR(200),
    hq_country VARCHAR(100),
    office_locations TEXT[],

    -- Funding & growth
    funding_stage VARCHAR(50), -- seed, series_a, series_b, public, etc
    last_funding_amount DECIMAL(15,2),
    last_funding_date DATE,
    total_funding DECIMAL(15,2),
    investors TEXT[],

    -- Technology
    technologies_used TEXT[],
    tech_stack JSONB,
    tech_spend_estimate DECIMAL(12,2),

    -- Growth signals
    growth_signals TEXT[],
    hiring_status VARCHAR(50), -- actively_hiring, stable, downsizing
    job_openings_count INT DEFAULT 0,
    recent_news TEXT[],

    -- Qualification
    prospect_score INT DEFAULT 0,
    fit_score INT DEFAULT 0,
    urgency_score INT DEFAULT 0,
    qualification_status VARCHAR(20) DEFAULT 'new', -- new, qualified, contacted, opportunity, customer, lost

    -- Contact attempts
    contacted BOOLEAN DEFAULT FALSE,
    contact_attempts INT DEFAULT 0,
    last_contact_date TIMESTAMP,

    -- Metadata
    discovered_at TIMESTAMP DEFAULT NOW(),
    last_enriched TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Decision makers and contacts
CREATE TABLE IF NOT EXISTS prospect_contacts (
    id SERIAL PRIMARY KEY,
    company_id INT REFERENCES prospect_companies(id) ON DELETE CASCADE,

    -- Personal information
    name VARCHAR(200),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    job_title VARCHAR(100),
    department VARCHAR(100),
    seniority_level VARCHAR(50), -- C-level, VP, Director, Manager, Individual Contributor

    -- Contact information
    email VARCHAR(200),
    email_verified BOOLEAN DEFAULT FALSE,
    phone VARCHAR(50),
    phone_verified BOOLEAN DEFAULT FALSE,
    linkedin_url TEXT,
    twitter_handle VARCHAR(100),

    -- Scoring
    decision_maker_score INT DEFAULT 0, -- 0-100, likelihood they're a decision maker
    influence_level VARCHAR(50), -- high, medium, low

    -- Contact tracking
    contact_attempted BOOLEAN DEFAULT FALSE,
    contact_method VARCHAR(50), -- email, linkedin, phone, cold_call
    contact_status VARCHAR(20) DEFAULT 'new', -- new, contacted, responded, qualified, meeting_set, customer

    -- Metadata
    discovered_at TIMESTAMP DEFAULT NOW(),
    last_contact_attempt TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Outreach tracking
CREATE TABLE IF NOT EXISTS outreach_log (
    id SERIAL PRIMARY KEY,
    company_id INT REFERENCES prospect_companies(id),
    contact_id INT REFERENCES prospect_contacts(id),

    -- Outreach details
    outreach_type VARCHAR(50) NOT NULL, -- email, linkedin, phone, direct_mail
    subject_line TEXT,
    message_content TEXT,
    personalization_level VARCHAR(50), -- low, medium, high

    -- Campaign information
    campaign_name VARCHAR(200),
    sequence_step INT DEFAULT 1,

    -- Response tracking
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP,
    replied_at TIMESTAMP,
    reply_content TEXT,
    sentiment VARCHAR(20), -- positive, neutral, negative

    -- Outcome
    outcome VARCHAR(50), -- no_response, interested, not_interested, meeting_set, unsubscribed
    next_action VARCHAR(100),
    next_action_date TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_companies_score ON prospect_companies(prospect_score DESC, qualification_status);
CREATE INDEX IF NOT EXISTS idx_companies_industry ON prospect_companies(industry, employee_count_range);
CREATE INDEX IF NOT EXISTS idx_companies_status ON prospect_companies(qualification_status, discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_contacts_company ON prospect_contacts(company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_score ON prospect_contacts(decision_maker_score DESC, seniority_level);
CREATE INDEX IF NOT EXISTS idx_outreach_company ON outreach_log(company_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outreach_contact ON outreach_log(contact_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_outreach_outcome ON outreach_log(outcome, sent_at DESC);

-- ============================================================================
-- SHARED UTILITY TABLES
-- ============================================================================

-- API rate limit tracking (if using database instead of Redis)
CREATE TABLE IF NOT EXISTS api_rate_limits (
    id SERIAL PRIMARY KEY,
    api_name VARCHAR(100) NOT NULL,
    endpoint VARCHAR(200),
    request_timestamp TIMESTAMP NOT NULL,
    tool_name VARCHAR(100),
    user_id VARCHAR(100),
    success BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_api ON api_rate_limits(api_name, request_timestamp DESC);

-- Tool execution metrics
CREATE TABLE IF NOT EXISTS tool_metrics (
    id SERIAL PRIMARY KEY,
    tool_name VARCHAR(100) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    duration_ms INT NOT NULL,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    parameters JSONB,
    executed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_tool ON tool_metrics(tool_name, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_success ON tool_metrics(success, tool_name);

-- ============================================================================
-- TRIGGER FUNCTIONS FOR AUTOMATIC TIMESTAMPS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to relevant tables
CREATE TRIGGER update_arbitrage_products_updated_at BEFORE UPDATE ON arbitrage_products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_data_collection_jobs_updated_at BEFORE UPDATE ON data_collection_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prospect_companies_updated_at BEFORE UPDATE ON prospect_companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR REPORTING
-- ============================================================================

-- Arbitrage opportunities view
CREATE OR REPLACE VIEW v_top_arbitrage_opportunities AS
SELECT
    id,
    product_title,
    source_platform,
    target_platform,
    source_price,
    target_price,
    estimated_profit,
    profit_margin,
    roi_percentage,
    rating,
    status,
    created_at
FROM arbitrage_products
WHERE status = 'discovered'
  AND profit_margin > 0.20
ORDER BY profit_margin DESC, estimated_profit DESC
LIMIT 100;

-- High-value leads view
CREATE OR REPLACE VIEW v_qualified_leads AS
SELECT
    id,
    company_name,
    contact_name,
    job_title,
    email,
    company_size,
    industry,
    lead_score,
    qualification_status,
    discovered_at
FROM leads
WHERE lead_score >= 70
  AND email IS NOT NULL
  AND qualification_status IN ('qualified', 'new')
ORDER BY lead_score DESC;

-- Top prospect companies view
CREATE OR REPLACE VIEW v_top_prospects AS
SELECT
    id,
    company_name,
    industry,
    employee_count,
    funding_stage,
    prospect_score,
    contacted,
    qualification_status,
    discovered_at
FROM prospect_companies
WHERE prospect_score >= 70
  AND contacted = FALSE
ORDER BY prospect_score DESC
LIMIT 100;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
