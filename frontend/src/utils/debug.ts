/**
 * Проверяет доступность API с разными настройками CORS для отладки
 */
export async function testCorsSettings() {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  
  console.log('Testing CORS settings with various credentials options...');
  
  // Тест 1: без учетных данных
  try {
    const resp1 = await fetch(`${apiUrl}/health`, { 
      credentials: 'omit',
      headers: { 'Accept': 'application/json' },
    });
    console.log('Test 1 (credentials: omit):', resp1.status, resp1.ok);
  } catch (e) {
    console.error('Test 1 failed:', e);
  }
  
  // Тест 2: с учетными данными для same-origin
  try {
    const resp2 = await fetch(`${apiUrl}/health`, { 
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' },
    });
    console.log('Test 2 (credentials: same-origin):', resp2.status, resp2.ok);
  } catch (e) {
    console.error('Test 2 failed:', e);
  }
  
  // Тест 3: с учетными данными для всех запросов
  try {
    const resp3 = await fetch(`${apiUrl}/health`, { 
      credentials: 'include',
      headers: { 'Accept': 'application/json' },
    });
    console.log('Test 3 (credentials: include):', resp3.status, resp3.ok);
  } catch (e) {
    console.error('Test 3 failed:', e);
  }
  
  console.log('CORS tests completed');
}
