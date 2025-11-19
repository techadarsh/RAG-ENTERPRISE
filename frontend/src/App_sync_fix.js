// This is a partial replacement for the handleSync function
  // Sync Confluence data
  const handleSync = async () => {
    setIsSyncing(true);
    setSyncMessage('Syncing...');
    try {
      const response = await axios.post(`${API_BASE_URL}/api/confluence/sync-now`);
      if (response.data && response.data.status === 'success') {
        const { new: newCount, updated, deleted, unchanged, total } = response.data;
        
        setSyncMessage(
          `✅ Sync Complete\n` +
          `📄 ${newCount} new\n` +
          `🔄 ${updated} updated\n` +
          `🗑️ ${deleted} deleted\n` +
          `✓ ${unchanged} unchanged\n` +
          `Total: ${total} pages`
        );
        // Refresh topics after sync if there were changes
        if (newCount > 0 || updated > 0 || deleted > 0) {
          fetchTopics();
        }
      } else {
        setSyncMessage(`⚠️ Sync error\n${response.data.message || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Sync failed:', err);
      setSyncMessage(`❌ Sync failed\n${err.response?.data?.detail || err.message}`);
    } finally {
      setIsSyncing(false);
      // Clear message after 10 seconds (longer for detailed message)
      setTimeout(() => setSyncMessage(''), 10000);
    }
  };
