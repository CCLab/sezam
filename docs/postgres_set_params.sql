ALTER ROLE postgres IN DATABASE sezam SET client_encoding = 'UTF8';
ALTER ROLE postgres IN DATABASE sezam SET default_transaction_isolation = 'read committed';
ALTER ROLE postgres IN DATABASE sezam SET timezone = 'UTC'