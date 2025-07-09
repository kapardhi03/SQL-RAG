CREATE TABLE description_table (
    id bigserial PRIMARY KEY,
    t_name TEXT,
    description TEXT
);

CREATE TABLE services (
    id bigserial PRIMARY KEY,
    s_no TEXT,
    chapter_section_heading TEXT,
    description TEXT,
    cgst_rate DECIMAL(5,2),
    sgst_utgst_rate DECIMAL(5,2),
    igst_rate DECIMAL(5,2),
    condition TEXT
);

CREATE TABLE goods (
    id bigserial PRIMARY KEY,
    schedule TEXT,
    s_no TEXT,
    chapter_heading TEXT,
    description TEXT,
    cgst_rate DECIMAL(5,2),
    sgst_utgst_rate DECIMAL(5,2),
    igst_rate DECIMAL(5,2),
    compensation_cess DECIMAL(10,2)
);
