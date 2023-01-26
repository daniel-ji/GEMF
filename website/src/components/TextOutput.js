import React, { Component } from 'react'

export class TextOutput extends Component {
  render() {
        return (
            <div className="output my-3">
                {this.props.label && 
                <h3 className="w-100 text-center">{this.props.label} &nbsp;
                    <input className="form-check-input my-1" type="checkbox" checked={this.props.downloadFile} id={this.props.id} onChange={this.props.toggleDownloadFile} />
                </h3>
                }
                <textarea id={this.props.id} className="form-control" readOnly value={this.props.text} />
            </div>
        )
    }
}

export default TextOutput