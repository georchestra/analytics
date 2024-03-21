
CREATE SCHEMA ogcstatistics ;

CREATE TABLE ogcstatistics.ogc_services_log (
  user_name varchar(255) NULL,
  "date" timestamp NULL,
  service varchar(5) NULL,
  layer varchar(255) NULL,
  id bigserial NOT NULL,
  request varchar(20) NULL,
  org varchar(255) NULL,
  roles _text NULL
);

