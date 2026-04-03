--
-- PostgreSQL database dump
--

\restrict Dz4JfdXN8vWsSjyndt5wefmnCx3c2rnA5XKHr0sH1ShpaAZ9BoeXHi7Xhf8yg3T

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
INSERT INTO public.credentials_entity VALUES ('Google Sheets account', 'U2FsdGVkX19n9dGBDJbr9spSUliWqcEwTQzwmflwl+RHQTSiNFhOgntI3EPVUFyPZPEbyFSZ1BK7TZF7WOrOM2PXZ79KBrtm/3nMJjwy5WV62mgwMppf4IQVO8r0F3SZvthftpw1Qy0eNRCKXA2Zik/pXJLOKRzX9BQmdonq4dwKWrp6it8n7WIsx4A8atD+stQ40UKp1a7hvgeW0Sd8kN4vjiqmNY8lruNVVreAtkBWpIecERIIy9DLMS7dqHcnAqqhuQSD36lo40izQbhbB2wKFimof3hhcSVYd5hwWagL8JWye6WBwxS2/WQKtiFdtr6OJHbYUsOxKbsX22nJZ11iRUJgHX6QTVeFIOV5wCtAsoTU8J7cP3NxqtSmtkThHM6b7BJwmFIiUzxp13lEZgX3QsEtF7IV7NGFK3JDz0zjvyANOrZNIeI4CH2l9+yCtpXxJabRvNttVnDYpwupUEndL1uCkvkCVBeHv1BpgeE2EekLCsyaGArkJIRLplJICCLRGEw+YXUIO/4jgrAivirhxsqrrDevxjKzp1kGeZrzfPz1QHyJpsNUHJSV0Y4Q7HnpYP2TXExPpxxB/JcVPWguE9Bw7zY6/hPCCrVytL7p0GDe+oGSb4GoKdWRVpIhkMNRul2mbwSMtZ86lsThnmvYby4ngTWuPSFMi7yPvlde9INd9yx1jpbnshiWIQMqhObgnl5WkyrJ+widjpYMqVcr52LCilpPizOD6/ok02WYR71q/2zR4i5RcTbb7XrXLGKmxfUgVfCi1jarXkVURLaMhGjD3blOixAs6Q48PydfECQUUAdwc05EOj/GgWSgyydK/5Pt/6U4dfy51usUwt/+N7E/npP3slusXpoyDV990dG3Ym0aEzGL7vR1N6MSq6jMfYDbY2qH5C0GkfCWRt4KGhDG/R4CRjav4RE90UZaRtRqSf6uPSvMCEKMk870fKCvs2lKLU46palz5gyUCqfn92/gGMsTBB2eWqG/Io+sv743Z7KZDYr2WIIAHPiITYnyRBk+qQHUkjQF8zn7POm9y6sZ8Ulzb3CHRqO+MiUtJEVYz5Gf5NE9MkAlmNqV8vhwllQaILRHYrxmK+YXl5YTZXoaWcc3A/2ZP271w2lIH1lEGqg8av/PkbVC+mXzB65uNRD82iDdGCvHxOYFSL0yGkRzkhA9jSseDAHvqCHc5Fy3eNnsFsJk2DhxjolTPIU4jux1mC5UxYBt3kftSoxA03QGj0txYrIr1inqBXchr5CxgCcDetcTlUyJLG2z', 'googleSheetsOAuth2Api', '2026-02-14 01:26:54.846+00', '2026-03-21 20:33:07.135+00', 'iO2m5SZwxG1viR46', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('polza.ai', 'U2FsdGVkX19Y8BZyXy3M+U8llfRhA2wzbYuu7MjzUEhYlQZO3RbsHxatzjd5AFneyPY6pXR2cA/6oI57r43eY42+DxOwfgAYXPe+wiHKwv77R2TLchs8ncb5zSYXpyb9gO2M12F0bYCCZapoJydTDA==', 'openAiApi', '2026-03-21 20:09:06.09+00', '2026-03-21 20:13:42.385+00', 'oyDHju4LEcPX94u4', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Neuroapi', 'U2FsdGVkX18bjVjKtu+wX+ZYGo9lAdQ1RkJz6d5KWjnlNTpeOWo2K28NAWzxevhUW39wNupDK6a7F+4WVuOCyNvWgzim1m0RznSVoY9rxPhn3gTjHaeZePEJQGsobWMvtTSYQJfNJHBScc0I8jZ4uudjYjTAvwzFJPmQlA4ZXtU=', 'openAiApi', '2026-03-21 20:14:10.101+00', '2026-03-21 20:14:24.296+00', 'BsGSDSjRdNfiWliT', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Telegram account', 'U2FsdGVkX19lfCl/P6DBILpTWZnEeFC53vDKmk7znF33/CpXc3qnWD36puNToLyn16i9WG+WfeBUJPC4GWxsNZQ0r9v1v9toUDyz9qJrLRzKlnYgQdsUJsOcRZzfMRpM', 'telegramApi', '2026-03-21 20:54:32.175+00', '2026-03-21 20:54:32.162+00', 'V4jPr27PQcfRRHY9', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Polza', 'U2FsdGVkX18jfB03BLBGzuc/QAhYJI0CmVqJXYBz67LtbNGH/o+o59yi+slQhhRwDpabZRYptxhatr1yIvqoRhiY0SgKWtyy+QianG5FQD8eODNXsOIFQ7g75D9D4YCzSw79WxvmpDjYQSlouyB1SQ==', 'openAiApi', '2026-03-22 08:14:05.55+00', '2026-03-22 08:14:37.405+00', 'dw2ygQ53RyVkCAva', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Postgres account', 'U2FsdGVkX19/3cTDBPT1TXS6STuKe/tUwbsSkLzLd9/Ya3Hhv4hE2/jYIOsyiiW8hu62foBNFeFBT1HUd4oO7Oi0sKUKfX4iZ5XamxCwiA8=', 'postgres', '2026-03-21 20:17:35.23+00', '2026-03-25 14:31:45.444+00', 'iGih4QSBWfmpkdGY', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('n8n account', 'U2FsdGVkX19cfZZ6+/chwEqQ6Ca3RTOrhbza+UrZaSNb1mhd1uh43VLrc64sihLpuSPimDDF+2/FpGlM53rW7pbfygea748c1XGJ7A3gKuFX/Q4+WV3pTiyVnGdhvM2q1eNwwIgsfuKFU/2yV2/W3bgoc2wrBAeBwuFgzgIJumGZPaeXVZPwbx08YHAnE3B7q0jS4lVTb11s9tRMMfMQ9lx4IuoYZw6lzeTWKUaA7HPsurS5R1nwnpgG0GlR+gSaHA2g3D5muGv7KnI/sfh5YQniOo7WmUoR7ORrPVUlbQMmIMb2fD2hJLSoKx9VHAVk/rqTbqNMMm1LgiT8j40vYzh5gi6jwCNwVrBc6F8lkrZOCYCstdg9C0hRjV0BrE0hw4CoF2L/bwKpH54Xr905XwenW8wX6R1yD8+8aN0d3YyEcbOO81xHuh+sD6GfTKgORv5a4HOww7/Sf7JWChDy7Q==', 'n8nApi', '2026-03-22 06:38:57.353+00', '2026-03-25 11:58:41.001+00', 'VP4X78ps0YqOb1RP', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Aihubmix', 'U2FsdGVkX1+Fgd478Rp9k1Bd5MutyFpFKIrcGn+7E9pijhIRM7ceIgbBugUe9x7PyKa6N4SsGRvaxicgCJxKJctNmMyzevMNMFEhIX0nIetx/fMqzRWntZ5MnYsyALB7Yx2k3Wqbd95Up2w597zDLR6pDKha7jIWAo5w1i6O2Q4=', 'openAiApi', '2026-03-29 16:14:37.538+00', '2026-03-29 16:17:41.482+00', 'pr0cxHPL3Uk4gtSf', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('LightRag', 'U2FsdGVkX1+6Gk5zg/8q/RIZ7UIKhUVgkByiS7FWo2aJTY0ET7+ljRl92KzVB/8dGk1KfuymH5ihITvE659s/A==', 'httpHeaderAuth', '2026-03-31 19:06:49.623+00', '2026-03-31 19:07:09.4+00', '04F0dXlIVNesjJse', false, false, false, false, NULL);
INSERT INTO public.credentials_entity VALUES ('Google Drive account', 'U2FsdGVkX19VvFyA5p+rpD2etfaCzt/hB/u6d0u4ztUTyZKLeonAUP5zwP6Bgj7Okv0dr3sOxol0P4Gh8Qu8RmrJ+Es7t/11qxtXabmDJtr8gb+fr8CTc6qCFOUAEszbXjqK0lk4/zWN+PsSdvEyQyFJ1VqkDqk9alWbK+ZcfopWaaVuDlPefRvBp4dUMETKF9/mTQ1xYBpZGNMbpMZkGH2gutl8EQvltmLM5FS+Czt6772ZkhqLNyr2myZoIi+BOcgRJdTp1nli2Po/Ne+R8Lg21ZxAYQZ7m3eM7FPCaffvD/pzMyzx86QiyPfxMfLSmjBDf4/mefYVkASOeRjsgIIbF3pM5VS+lLLCOxdvih1dkyDSpcvPMygoEEG5jSlgt4G5uiU/PTYk/TFKQkHTdaatHM2kUX+IDshHiNszCf/GB9aJyYVEIv1l4wsfjRY8ZjT1hzDb1/uvraR9CcKxyvnBcHO1Gdkz4jrfinCstX4mNQ2t/1Ow0amcOMZdsVNgrqP2yy7qEvcXaupzJe7FTSCaY9xj4bRyyhsipkV12JjN75N1Zv60g/jm4ID0EvzK6GR9ULJhdhQ+eGLv2XyfEBhlVHAyUcoSq6bg/8EOlcZkSIziz6JBzrK1SbixfZKaJq5ypdaPOIKWZt1mcRn9h7WQP28gD5qDYM4ynyVy9xEoF35l/PIjL31oayhbRfjrLFW0Z6bYp3I3+tRC/RrhrVt9FkkHv437rSS0I6ECAaq257VDZrK3YJxbdp8oEDAwWUKl+WpswVXBhlIgVPIzGK3a3aa8p0khH/sUBvo6qn5AHgNQOUL1Pce+0UJpAeMMCg7HkYnGeJ/cveTAc82lo/iNYgy3zJoHq+Eq4o+Sswen7w01fmP3cjK4juVOBnaVzRDK3g/l4ynMGPO0P2PDxs9jJ8lGJMHzkC06UFKteOE/sG1DZ8JRzbCQWWG/OOpJeMTKyYrPOmVQMxNmKi/JTYXF8RThq+HG9jjh/TrT49sZlYcBOnizSkjX4UrAi6let+vBCfyfES6cVLzBKlYwy0xs3XbZ4w9Jp2OJ5bN6AniDL8HaDm+PIrl9QCkDxCCPDkpGCz3/jXjxvDdpVljMU+arkSCvb+Tgq77oLSqD050jGo1LH6e1w4FUs8RUvtzjV7CZnvRSa6q8zLlBenXbH2WwiI8ulVUZXAZTbtOvIPMWdw/IZyAB65pOS48+4PLPUYPpmru700ox/ZuuCMMfFHRiCLs3di+zI/PPBRpT5Cc5Hnl1GMTZx89SjQqdeZjBWE92hWug/5KioHV3eJUdnQ==', 'googleDriveOAuth2Api', '2026-02-11 06:20:44.587+00', '2026-04-03 07:49:31.536+00', 'OfjqR7v8bwrPeQgK', false, false, false, false, NULL);


--
-- PostgreSQL database dump complete
--

\unrestrict Dz4JfdXN8vWsSjyndt5wefmnCx3c2rnA5XKHr0sH1ShpaAZ9BoeXHi7Xhf8yg3T

