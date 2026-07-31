import { redirect } from 'next/navigation';

export default function GridPage() {
<<<<<<< HEAD
  const [instances, setInstances] = useState<TradingInstance[]>([]);
  const [selectedInstance, setSelectedInstance] = useState('');
  const [gridState, setGridState] = useState<GridStateData | null>(null);
  const [loading, setLoading] = useState(false);

  const loadInstances = useCallback(async () => {
    try {
      const insts = await api.listTradingInstances();
      setInstances(insts || []);
    } catch {
      setInstances([]);
    }
  }, []);

  const loadGridState = useCallback(async () => {
    if (!selectedInstance) {
      setGridState(null);
      return;
    }
    setLoading(true);
    try {
      const state = await api.getGridState(selectedInstance);
      setGridState(state as GridStateData);
    } catch {
      setGridState(null);
    } finally {
      setLoading(false);
    }
  }, [selectedInstance]);

  useEffect(() => {
    loadInstances();
    const interval = setInterval(loadInstances, 5000);
    return () => clearInterval(interval);
  }, [loadInstances]);

  useEffect(() => {
    loadGridState();
    const interval = setInterval(loadGridState, 3000);
    return () => clearInterval(interval);
  }, [loadGridState]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Grid Visualization</h1>
        <p className="text-muted-foreground">Live grid levels for your trading bots</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Trading Bot</CardTitle>
          <CardDescription>Choose a trading instance to view its grid levels</CardDescription>
        </CardHeader>
        <CardContent>
          {instances.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No trading instances found. Create a bot from the Trading page first.
            </p>
          ) : (
            <div className="space-y-2">
              {instances.map((inst) => (
                <label key={inst.id} className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="radio"
                    name="instance"
                    value={inst.id}
                    checked={selectedInstance === inst.id}
                    onChange={(e) => setSelectedInstance(e.target.value)}
                  />
                  <div className="flex-1 flex items-center gap-3">
                    <span className="font-medium">{inst.symbol}</span>
                    <Badge variant={inst.status === 'running' ? 'success' : 'secondary'}>
                      {inst.status}
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      {inst.total_investment} USDT
                    </span>
                  </div>
                </label>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {selectedInstance && (
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>
                  {gridState?.symbol || 'Loading...'}
                  {gridState?.current_price && (
                    <span className="ml-3 text-lg font-normal text-muted-foreground">
                      ${formatNumber(gridState.current_price)}
                    </span>
                  )}
                </CardTitle>
                <CardDescription>
                  {gridState ? `${gridState.grid_count} grid levels` : 'Loading grid state...'}
                  {gridState && gridState.total_cycles > 0 && (
                    <span className="ml-2">
                      | {gridState.total_cycles} cycles | {gridState.total_profit.toFixed(2)} profit
                    </span>
                  )}
                </CardDescription>
              </div>
              <Button size="sm" variant="outline" onClick={loadGridState} disabled={loading}>
                {loading ? 'Loading...' : 'Refresh'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {!gridState || gridState.levels.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                {gridState?.status === 'no_grid'
                  ? 'Grid has not been initialized yet. Start the bot to begin grid trading.'
                  : 'No grid levels found. The bot may not be running.'}
              </p>
            ) : (
              <div className="space-y-2">
                {gridState.levels.map((level) => (
                  <div
                    key={level.index}
                    className="flex flex-col gap-2 rounded-md border p-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-muted-foreground">#{level.index}</span>
                      <Badge variant={level.side === 'buy' ? 'success' : 'destructive'}>
                        {level.side.toUpperCase()}
                      </Badge>
                      <div className="flex flex-col">
                        <span className="font-medium">${formatNumber(level.buy_price)}</span>
                        {level.sell_price > 0 && (
                          <span className="text-xs text-muted-foreground">
                            sell: ${formatNumber(level.sell_price)}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-muted-foreground">
                        {level.quantity} {gridState.symbol.replace('USDT', '').replace('BUSD', '')}
                      </span>
                      <Badge variant={statusColors[level.status] || 'secondary'}>
                        {level.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
=======
  redirect('/dashboard/strategy-setting?tab=grid');
>>>>>>> develop
}
