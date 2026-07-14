--
-- PostgreSQL database dump
--

\restrict 1mODcGerhDsbnPwTtFucnWoegVBq6fFgPHxPRhsXarG4TaJVMKImPAnwWdfdjpf

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ocr_jobs; Type: TABLE; Schema: public; Owner: n8n_user
--

CREATE TABLE public.ocr_jobs (
    id bigint NOT NULL,
    source_public_key text NOT NULL,
    source_path text NOT NULL,
    source_name text NOT NULL,
    source_md5 character(32) NOT NULL,
    output_path text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    confidence numeric(8,6),
    min_confidence numeric(8,6),
    line_count integer,
    text_length integer,
    ocr_engine text,
    ocr_version text,
    error_message text,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ocr_jobs_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'processing'::text, 'done'::text, 'retry'::text, 'failed'::text])))
);


ALTER TABLE public.ocr_jobs OWNER TO n8n_user;

--
-- Name: ocr_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: n8n_user
--

CREATE SEQUENCE public.ocr_jobs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ocr_jobs_id_seq OWNER TO n8n_user;

--
-- Name: ocr_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: n8n_user
--

ALTER SEQUENCE public.ocr_jobs_id_seq OWNED BY public.ocr_jobs.id;


--
-- Name: ocr_jobs id; Type: DEFAULT; Schema: public; Owner: n8n_user
--

ALTER TABLE ONLY public.ocr_jobs ALTER COLUMN id SET DEFAULT nextval('public.ocr_jobs_id_seq'::regclass);


--
-- Name: ocr_jobs ocr_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: n8n_user
--

ALTER TABLE ONLY public.ocr_jobs
    ADD CONSTRAINT ocr_jobs_pkey PRIMARY KEY (id);


--
-- Name: ocr_jobs ocr_jobs_source_public_key_source_path_key; Type: CONSTRAINT; Schema: public; Owner: n8n_user
--

ALTER TABLE ONLY public.ocr_jobs
    ADD CONSTRAINT ocr_jobs_source_public_key_source_path_key UNIQUE (source_public_key, source_path);


--
-- Name: idx_ocr_jobs_status_updated; Type: INDEX; Schema: public; Owner: n8n_user
--

CREATE INDEX idx_ocr_jobs_status_updated ON public.ocr_jobs USING btree (status, updated_at);


--
-- PostgreSQL database dump complete
--

\unrestrict 1mODcGerhDsbnPwTtFucnWoegVBq6fFgPHxPRhsXarG4TaJVMKImPAnwWdfdjpf

