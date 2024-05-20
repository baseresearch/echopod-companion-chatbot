-- Create User table
CREATE TABLE "User" (
  user_id SERIAL PRIMARY KEY,
  username VARCHAR(255) NOT NULL
);

-- Create OriginalText table
CREATE TABLE OriginalText (
  text_id SERIAL PRIMARY KEY,
  lang VARCHAR(50) NOT NULL,
  text TEXT NOT NULL
);

-- Create Translation table
CREATE TABLE Translation (
  translation_id SERIAL PRIMARY KEY,
  original_text_id INTEGER REFERENCES OriginalText(text_id),
  user_id INTEGER REFERENCES "User"(user_id),
  lang VARCHAR(50) NOT NULL,
  text TEXT NOT NULL
);

-- Create Score table
CREATE TABLE Score (
  score_id SERIAL PRIMARY KEY,
  translation_id INTEGER REFERENCES Translation(translation_id),
  user_id INTEGER REFERENCES "User"(user_id),
  score_value INTEGER NOT NULL
);

-- Create indexes
CREATE INDEX idx_translation_original_text_id ON Translation(original_text_id);
CREATE INDEX idx_translation_user_id ON Translation(user_id);
CREATE INDEX idx_score_translation_id ON Score(translation_id);
CREATE INDEX idx_score_user_id ON Score(user_id);

-- Create application user with restricted permissions
CREATE USER chatbot_app WITH PASSWORD 'secure_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON "User", OriginalText, Translation, Score TO chatbot_app;