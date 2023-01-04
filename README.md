# aws-role-session

Python package to simplify cross-account access

## Introduction

On AWS, a [multi-account](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/organizing-your-aws-environment.html) architecture is often employed to establish a solid foundation for an environment. A common setup to allow users to access the environment is depicted in, figure 1:

|                              ![](/docs/aws_multi_account.png)                               |
| :-----------------------------------------------------------------------------------------: |
| <b>Fig.1 - Schmatic overview of IAM users and privileges in a multi-account environment</b> |

IAM (user) accounts are created in one root account (the IAM account). Access to and specific privileges in the other root accounts (for example, the Application account) are provided by roles. An IAM user is assigned privileges to use the [AssumeRole API operation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use.html) to assume (or switch to) these roles.

## Configuration

The configuration of this module

### AWS credentials

The basis for

### Configuration file

<br>
## Usage
<br>
## Limitations

## License

This code is licensed under the MIT license. Please see `LICENSE` for full text.

## Contributing

1. Fork it on GitHub (https://github.com/lvvloten/aws-role-session)
1. Create your feature branch (`git checkout -b feature/my-new-feature`)
1. Commit your changes (`git commit -am 'Add some feature'`)
1. Push to the branch (`git push origin feature/my-new-feature`)
1. Create a new Pull Request (on [GitHub](https://github.com))
