# Run all LLM-related endpoint tests (PowerShell)
# Usage: Open PowerShell, ensure backend is running, then run this script.

# --------- 1) Login and get token ---------
$loginBody = @{
    email = "john.doe@example.com"
    password = "Test@1234"
} | ConvertTo-Json

Write-Host "Logging in..."
$loginResp = Invoke-WebRequest -Uri "http://localhost:5000/api/auth/login" `
  -Method POST -ContentType "application/json" -Body $loginBody

$token = ($loginResp.Content | ConvertFrom-Json).access_token
Write-Host "Token: $($token.Substring(0,30))..."

# --------- 2) Generate questions ---------
$body = @{
  topic = "Python Async/Await"
  level_description = "Intermediate: 2-step application"
  concept_tag = "async_programming"
  count = 2
  user_id = "user_123"
} | ConvertTo-Json

Write-Host "\nGenerating questions..."
$response = Invoke-WebRequest -Uri "http://localhost:5000/api/llm/questions/generate" `
  -Method POST -Headers @{ "Authorization" = "Bearer $token" } `
  -ContentType "application/json" -Body $body

$data = $response.Content | ConvertFrom-Json
Write-Host "Generated: $($data.generated)   Verified: $($data.verified)"
$data.questions | ForEach-Object { Write-Host "Q: $($_.question)"; Write-Host "Options: $($_.options -join ' | ')" }

# --------- 3) Request explanations for first question ---------
if ($data.questions -and $data.questions.Count -gt 0) {
    $q = $data.questions[0]
    $questionDoc = @{
      question = $q.question
      options = $q.options
      correct_index = $q.correct_index
      concept_tag = $q.concept_tag
      difficulty = $q.difficulty
    }

    $body = @{ question_doc = $questionDoc } | ConvertTo-Json -Depth 6

    Write-Host "\nRequesting explanation..."
    $resp = Invoke-WebRequest -Uri "http://localhost:5000/api/explain/generate" `
      -Method POST -Headers @{ "Authorization" = "Bearer $token" } -ContentType "application/json" -Body $body

    $result = $resp.Content | ConvertFrom-Json
    if ($result.error) {
      Write-Host "Error from backend:" $result.error
    } elseif ($result.flagged -eq $true) {
      Write-Host "Explanation flagged for admin review. Verifier output:"
      $result.verifier | ConvertTo-Json -Depth 6 | Write-Host
    } else {
      Write-Host "Answer Explanation:"
      Write-Host $result.explanations.answer_explanation
      Write-Host "`nOption explanations:"
      $result.explanations.option_explanations | ForEach-Object {
        Write-Host ("Option {0}: {1}" -f $_.option_index, $_.explanation)
      }
    }
}

# --------- 4) Generate micro-lesson ---------
$body = @{
  concept = "async_programming"
  mastery = 28
  user_id = "user_123"
} | ConvertTo-Json

Write-Host "\nGenerating micro-lesson..."
$resp = Invoke-WebRequest -Uri "http://localhost:5000/api/llm/microlesson/generate" `
  -Method POST -Headers @{ "Authorization" = "Bearer $token" } `
  -ContentType "application/json" -Body $body

$ml = $resp.Content | ConvertFrom-Json
if ($ml.error) {
  Write-Host "Micro-lesson generation error:" $ml.error
} else {
  Write-Host "Lesson text:"
  Write-Host $ml.lesson.lesson_text
  Write-Host "`nExamples:`"
  $ml.lesson.examples | ForEach-Object { Write-Host "- $_" }
  Write-Host "`nPractice questions:`"
  $ml.lesson.practice_questions | ForEach-Object { Write-Host ("Q: {0}`nOptions: {1}" -f $_.question, ($_.options -join ' | ')) }
}

# --------- 5) Extract interests ---------
$body = @{
  text = "I really enjoy building web apps with React and I'm learning machine learning models."
} | ConvertTo-Json -Depth 6

Write-Host "\nExtracting interests..."
$resp = Invoke-WebRequest -Uri "http://localhost:5000/api/llm/interest/extract" `
  -Method POST -Headers @{ "Authorization" = "Bearer $token" } `
  -ContentType "application/json" -Body $body

$int = $resp.Content | ConvertFrom-Json
Write-Host "Top topics: $($int.top_topics -join ', ')"
Write-Host "Merged weights (if returned):"
$int.merged_weights | ConvertTo-Json -Depth 5 | Write-Host
Write-Host "Confidence: $($int.confidence)"

Write-Host "\nLLM tests complete."
