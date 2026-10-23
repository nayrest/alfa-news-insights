import { Component, type ReactNode } from 'react';

// Падение одного экрана не должно оставлять пользователя с пустой страницей.
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="error">
        Что-то пошло не так: {this.state.error.message}{' '}
        <button className="btn btn--outline" onClick={() => this.setState({ error: null })}>Повторить</button>
      </div>
    );
  }
}
