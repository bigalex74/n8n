--
-- PostgreSQL database dump
--

\restrict a9m6zOxPlVAjJaJuo6AWkA2sjSFcAqDNrlJZ0AohHepiFErdb67PaVSKGxnCm1B

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

--
-- Data for Name: credentials_entity; Type: TABLE DATA; Schema: public; Owner: n8n_user
--

INSERT INTO public.credentials_entity VALUES ('Google Docs account 4', 'U2FsdGVkX19sywz9vbeoauJnqkE4U2WMsus5G+St2bXQPLjeYD8gD9x+K/BGXYt7aw6JEDoVgYGaH/FeV30BYniCLWWLvOigvePcEeg+5Xw5ENR/1108I2DtTbXYHF6IRBwORVk9DUGgKZHS4Sj/nlfo5YPOt0vBBroNFRzhh/nVn8ldnqWY84DI4XtEqWuM9RNGaoiy56/iV19XDTm2bPAt54eM8hwpHCkQC4TeS9gHkw8+j+vrMyeKv7diJIwQE7vtri9RDclHSwY5h1vz2WlGTyZz4rF9M2BDP1iHy89Dvy1P8WAq3atPTX4ctUitI+aOTjjzd6JAjfHX3+fHwDbrEdapskfHw1VfIu9DH2yyCwBM/OW1u2Pj2Glf00wVYIPhPdBRFYSk7uBrtDvdNYJxx76FYoP9kfAu5Rmtqa3msppNbRXH20Ex61FgvH72H7/Px8K8xV0mvu+aYFmDimSdFyRNxV3PX8vW6R+Hu+HnAlrVI/zkakabNTSn+1XD5i3sh45yzxRy76j5PMquav8umeboh/ncJ4gnUpa36eO7awMh60HPQJ1hf366B3NCvhI61k51zh9EFUl849/0xt6wUraZT6171PgNoAEYclvq+nL933KQP6bJSF3Saymevy5M2mn49qctjupS1qtNKMg89xA4acI+jCx7BhIlVsTkJqlJysddkoRzjZsyIkopWAPUb3vGKuOuZjpsjs8Fw727ext0q9lKStvJBlLSGphQvvf4ZVj8s4hwIxAOQvlIS39WK2GyiagmDfiD5cwDVrWgsJBSUieAvD9H24+1F0erSPq/GE6sdn4CBFOdBrhBUowvu2+3N55sJLkIroeOOgZ6LLJyT72/jtwZfCuVd4U6580Q64X84fjChPDjdnf9+nRxZ9sbNysls1H0YhBOUxvIhFOMcCx5kTkvC+No+Wok5B4yzASttX/Ieg39DEdBwigZ+PqkqGQBcY/Qq/RZxqn7LqoVLgF/U7lusdEw7JYx3bj1xd/PINqn4h5hVG/cZaMsplHGFo48JrEaOvPSKrt5p9jbksd1DHVCAqAXnZbewzyNXwUnLPubLXbl6MiR4cr+X1gChJRxMYcN0pnfpghllbzV+HNG7PoT9Qlz9NUhr+0EzD0mtrafsBKyOhmx8xpYV9Fjn4yPPpBMFdZDNOoMQ4Wo4+MBrPD1YoWMLxIhsblXPZdzjAb5eH6KZ2hxI1a2jLD36Z7IF7Ixxycj8Ncoca0t4SYDGFtSNMae6zw=', 'googleDocsOAuth2Api', '2026-02-10 00:51:58.362+00', '2026-03-21 20:32:20.345+00', 'SqXF6s0JBNHV3lVZ', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Google Drive account', 'U2FsdGVkX19jwsXiqmpt7O9sqbYdrYiRh6PlgOcNB2Jw32OGQFLg/86vZ85YJ3SFYkwco8UY+QycF/+cL9TA8l4x8zJ59D1eQvA2kPTuwH1Zh+OA+dFpBYoWm6BQ2vCMfLR/12+wzHaL4sjqKQxPTphC2eUmK7OcNMxM5aoVKwJncJWSdhzxS7qyHlmUdM+voVd+m/0QOPGAK9RDrcvcFLy8oLFD545eQDVk/33tYdXq74QwuGxmQbVEymvmamMGn7fQ6UHeChzzsgIjv9SRyND9v3DmgPwWMY4OGkMxqL193wFiyizmbHB3pIjJOdvbn2KrcQCLmTQVwFku2ZVeUWEi9VlXNad6QVq6x5KWD3GufogOTcgw6Mcky1PrGu3oMC77KX4Gl/4yzpOCxqSQmWpU54QLEIWswjw4H7+Htj2dh1ZmrGICErgHiIlxViSw2AYH3VXkE+4wEPZpWT4pmlPvWXN4miV7pC0jTUU8bGFYCYny3UrQkpeq3JiYU8li5/XEssa8YMya7VO5/gGey+gbSWWoy/LRApnVgIY0Y7dB1vuqkq+Jmf2nJIiENfhtIBpHtdMdiDGmIhPZv0426Vtkz28XzUogfc/Kh7Ed8oS3XPbiq7Hj3uD2+PWEgaPtwBXocQSN2YaY4frfm9DZLdrGOPPXeK5zxs73ccR9UCWYAPy0DvSpHM22yaaNxtgvNDW4azOCCrUBRVE6AuVorapbKyABmzsWGNgjv1lKpxRDCBnFbYE8Sw4sZA7OgYCuMiDvHdidMCp1gFjwZrFlJh8P7XhfXoCKzHtSaZzkYelPMk5okSzd9/6Y5gjub8yLmx2jMh/6HqURzE42X7um6oXNSXR0etzmrb879ogfQvHko2sLHvceisI1i0jYHSh+hXRB3GhdzRRWAyT6xyf/UAriXaJz3RQZFdvejGCqMSniAzsJCcl17j6OsfitQL1MUZP9Ali/ABgJ8r2E+MXLCw2CTFOfKyV93rJUrK6LxdM39rtuHEtjZPWmeANqU3Z2TwIL+r/8eVAIIlMyFJrF9NLzWZFLj1Bqih6T2a543oD9+ylLJbQnHU1C9K6VWRyYg3CrdTC6jXN3KHqj+IYxEWnmSYBkb9GRlBnT5dWgUYilGNxC2A7XDd3wk7HikU5ZcJRty0Omw0DjZ9yM3wjOrp6FaMCx8WEoYI0cQXgiVavlkaVD/GHpaLrLOoq+4owCPaoppXWMP6kwXqHnxhVCkm5rbiExGKQv2iRv7WAqlU0UFgO7w9NGD6q+lYRmLjmlSv/USC80mmSzwT7FPD3RKA==', 'googleDriveOAuth2Api', '2026-02-11 06:20:44.587+00', '2026-03-22 10:00:07.327+00', 'OfjqR7v8bwrPeQgK', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Google Sheets account', 'U2FsdGVkX19n9dGBDJbr9spSUliWqcEwTQzwmflwl+RHQTSiNFhOgntI3EPVUFyPZPEbyFSZ1BK7TZF7WOrOM2PXZ79KBrtm/3nMJjwy5WV62mgwMppf4IQVO8r0F3SZvthftpw1Qy0eNRCKXA2Zik/pXJLOKRzX9BQmdonq4dwKWrp6it8n7WIsx4A8atD+stQ40UKp1a7hvgeW0Sd8kN4vjiqmNY8lruNVVreAtkBWpIecERIIy9DLMS7dqHcnAqqhuQSD36lo40izQbhbB2wKFimof3hhcSVYd5hwWagL8JWye6WBwxS2/WQKtiFdtr6OJHbYUsOxKbsX22nJZ11iRUJgHX6QTVeFIOV5wCtAsoTU8J7cP3NxqtSmtkThHM6b7BJwmFIiUzxp13lEZgX3QsEtF7IV7NGFK3JDz0zjvyANOrZNIeI4CH2l9+yCtpXxJabRvNttVnDYpwupUEndL1uCkvkCVBeHv1BpgeE2EekLCsyaGArkJIRLplJICCLRGEw+YXUIO/4jgrAivirhxsqrrDevxjKzp1kGeZrzfPz1QHyJpsNUHJSV0Y4Q7HnpYP2TXExPpxxB/JcVPWguE9Bw7zY6/hPCCrVytL7p0GDe+oGSb4GoKdWRVpIhkMNRul2mbwSMtZ86lsThnmvYby4ngTWuPSFMi7yPvlde9INd9yx1jpbnshiWIQMqhObgnl5WkyrJ+widjpYMqVcr52LCilpPizOD6/ok02WYR71q/2zR4i5RcTbb7XrXLGKmxfUgVfCi1jarXkVURLaMhGjD3blOixAs6Q48PydfECQUUAdwc05EOj/GgWSgyydK/5Pt/6U4dfy51usUwt/+N7E/npP3slusXpoyDV990dG3Ym0aEzGL7vR1N6MSq6jMfYDbY2qH5C0GkfCWRt4KGhDG/R4CRjav4RE90UZaRtRqSf6uPSvMCEKMk870fKCvs2lKLU46palz5gyUCqfn92/gGMsTBB2eWqG/Io+sv743Z7KZDYr2WIIAHPiITYnyRBk+qQHUkjQF8zn7POm9y6sZ8Ulzb3CHRqO+MiUtJEVYz5Gf5NE9MkAlmNqV8vhwllQaILRHYrxmK+YXl5YTZXoaWcc3A/2ZP271w2lIH1lEGqg8av/PkbVC+mXzB65uNRD82iDdGCvHxOYFSL0yGkRzkhA9jSseDAHvqCHc5Fy3eNnsFsJk2DhxjolTPIU4jux1mC5UxYBt3kftSoxA03QGj0txYrIr1inqBXchr5CxgCcDetcTlUyJLG2z', 'googleSheetsOAuth2Api', '2026-02-14 01:26:54.846+00', '2026-03-21 20:33:07.135+00', 'iO2m5SZwxG1viR46', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('polza.ai', 'U2FsdGVkX19Y8BZyXy3M+U8llfRhA2wzbYuu7MjzUEhYlQZO3RbsHxatzjd5AFneyPY6pXR2cA/6oI57r43eY42+DxOwfgAYXPe+wiHKwv77R2TLchs8ncb5zSYXpyb9gO2M12F0bYCCZapoJydTDA==', 'openAiApi', '2026-03-21 20:09:06.09+00', '2026-03-21 20:13:42.385+00', 'oyDHju4LEcPX94u4', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Neuroapi', 'U2FsdGVkX18bjVjKtu+wX+ZYGo9lAdQ1RkJz6d5KWjnlNTpeOWo2K28NAWzxevhUW39wNupDK6a7F+4WVuOCyNvWgzim1m0RznSVoY9rxPhn3gTjHaeZePEJQGsobWMvtTSYQJfNJHBScc0I8jZ4uudjYjTAvwzFJPmQlA4ZXtU=', 'openAiApi', '2026-03-21 20:14:10.101+00', '2026-03-21 20:14:24.296+00', 'BsGSDSjRdNfiWliT', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Telegram account', 'U2FsdGVkX19lfCl/P6DBILpTWZnEeFC53vDKmk7znF33/CpXc3qnWD36puNToLyn16i9WG+WfeBUJPC4GWxsNZQ0r9v1v9toUDyz9qJrLRzKlnYgQdsUJsOcRZzfMRpM', 'telegramApi', '2026-03-21 20:54:32.175+00', '2026-03-21 20:54:32.162+00', 'V4jPr27PQcfRRHY9', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Polza', 'U2FsdGVkX18jfB03BLBGzuc/QAhYJI0CmVqJXYBz67LtbNGH/o+o59yi+slQhhRwDpabZRYptxhatr1yIvqoRhiY0SgKWtyy+QianG5FQD8eODNXsOIFQ7g75D9D4YCzSw79WxvmpDjYQSlouyB1SQ==', 'openAiApi', '2026-03-22 08:14:05.55+00', '2026-03-22 08:14:37.405+00', 'dw2ygQ53RyVkCAva', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Postgres account', 'U2FsdGVkX19/3cTDBPT1TXS6STuKe/tUwbsSkLzLd9/Ya3Hhv4hE2/jYIOsyiiW8hu62foBNFeFBT1HUd4oO7Oi0sKUKfX4iZ5XamxCwiA8=', 'postgres', '2026-03-21 20:17:35.23+00', '2026-03-25 14:31:45.444+00', 'iGih4QSBWfmpkdGY', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('n8n account', 'U2FsdGVkX19cfZZ6+/chwEqQ6Ca3RTOrhbza+UrZaSNb1mhd1uh43VLrc64sihLpuSPimDDF+2/FpGlM53rW7pbfygea748c1XGJ7A3gKuFX/Q4+WV3pTiyVnGdhvM2q1eNwwIgsfuKFU/2yV2/W3bgoc2wrBAeBwuFgzgIJumGZPaeXVZPwbx08YHAnE3B7q0jS4lVTb11s9tRMMfMQ9lx4IuoYZw6lzeTWKUaA7HPsurS5R1nwnpgG0GlR+gSaHA2g3D5muGv7KnI/sfh5YQniOo7WmUoR7ORrPVUlbQMmIMb2fD2hJLSoKx9VHAVk/rqTbqNMMm1LgiT8j40vYzh5gi6jwCNwVrBc6F8lkrZOCYCstdg9C0hRjV0BrE0hw4CoF2L/bwKpH54Xr905XwenW8wX6R1yD8+8aN0d3YyEcbOO81xHuh+sD6GfTKgORv5a4HOww7/Sf7JWChDy7Q==', 'n8nApi', '2026-03-22 06:38:57.353+00', '2026-03-25 11:58:41.001+00', 'VP4X78ps0YqOb1RP', false, false, false, false, NULL);


--
-- PostgreSQL database dump complete
--

\unrestrict a9m6zOxPlVAjJaJuo6AWkA2sjSFcAqDNrlJZ0AohHepiFErdb67PaVSKGxnCm1B

