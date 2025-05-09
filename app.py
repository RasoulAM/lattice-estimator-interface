from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy # Import SQLAlchemy
import datetime # To store timestamps
import math # Import math module for power function
from lattice_estimator.estimator import * # Assuming 'estimator' and its distributions (Binary, Ternary, DiscreteGaussian) are available in your environment
import json

# Create a Flask application instance
app = Flask(__name__)

# Configure the SQLite database
# This will create a file named 'queries.db' in your instance folder
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///queries.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Suppress a warning

# Initialize SQLAlchemy with the Flask app
db = SQLAlchemy(app)

# Define the database model for storing queries and results
class LWEQueryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Typed parameters
    n_param = db.Column(db.Integer, nullable=False)
    q_final_param = db.Column(db.BigInteger, nullable=False) # The calculated q value used in estimation
    secret_key_dist_param = db.Column(db.String(50), nullable=True) # e.g., 'binary', 'ternary', 'discretegaussian'
    sigma_s_param = db.Column(db.Float, nullable=True)
    sigma_e_param = db.Column(db.Float, nullable=True)
    hamming_weight_param = db.Column(db.Integer, nullable=True)
    m_param = db.Column(db.Integer, nullable=True)
    rough_param = db.Column(db.Boolean, nullable=False)

    result = db.Column(db.Text) # Store the full result string

# Define the database model for storing queries and results
class NTRUQueryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Typed parameters
    n_param = db.Column(db.Integer, nullable=False)
    q_final_param = db.Column(db.BigInteger, nullable=False) # The calculated q value used in estimation
    secret_key_dist_param = db.Column(db.String(50), nullable=False) # e.g., 'binary', 'ternary', 'discretegaussian'
    sigma_s_param = db.Column(db.Float, nullable=True)
    sigma_e_param = db.Column(db.Float, nullable=True)
    hamming_weight_param = db.Column(db.Integer, nullable=True)
    m_param = db.Column(db.Integer, nullable=True)
    ntru_type_param = db.Column(db.String(50), nullable=True) # e.g., 'matrix', 'circulant', 'fixed'
    rough_param = db.Column(db.Boolean, nullable=False)

    result = db.Column(db.Text) # Store the full result string

class SISQueryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Typed parameters
    n_param = db.Column(db.Integer, nullable=False)
    q_final_param = db.Column(db.BigInteger, nullable=False) # The calculated q value used in estimation
    length_bound_param = db.Column(db.Float, nullable=True)
    m_param = db.Column(db.Integer, nullable=True)
    rough_param = db.Column(db.Boolean, nullable=False)

    result = db.Column(db.Text) # Store the full result string    

# Define the route for the home page
@app.route('/')
def index():
    """Renders the main index.html page."""
    # This function will render the index.html file when the user visits the root URL.
    return render_template('index.html')

# Define the route for computation, accepting POST requests
@app.route('/compute', methods=['POST'])
def compute():
    """
    Receives parameters from the frontend, performs a computation,
    and returns the result as JSON. Handles 'q' or 'log_2 q' input
    and the secret key distribution type.
    """
    # Get data from the incoming POST request form.
    # request.form is a dictionary containing the form data sent from the frontend.
    n_str = request.form.get('n')
    q_value_str = request.form.get('q_value') # Get the value entered for q/logq
    q_type = request.form.get('q_type') # Get whether it's 'q' or 'logq'
    secret_key_dist_type = request.form.get('secret_key_dist') # Get the selected secret key distribution type
    sigma_e_str = request.form.get('sigma_e')
    sigma_s_str = request.form.get('sigma_s') # Get sigma_s, only used for DiscreteGaussian
    hamming_weight_str = request.form.get('hamming_weight')
    length_bound_str = request.form.get('length_bound')
    m_str = request.form.get('m')
    rough_str = request.form.get('rough') 

    problem = request.form.get('problem')

    # Log the query and result to the database
    try:
        n = int(n_str)
        q_value = float(q_value_str) # Convert the entered value to float
        if q_type == 'logq':
            # If input is log_2 q, calculate q = 2^(log_2 q)
            # math.pow(base, exponent) calculates base raised to the power of exponent
            q = int(math.pow(2, q_value))
        else: # Assume q_type is 'q' if not 'logq'
            # If input is q, use the value directly
            q = q_value
            # Ensure q is an integer if the type is 'q'. float.is_integer() checks if a float has no fractional part.
            if not q.is_integer():
                # If it's not an integer, raise a ValueError
                raise ValueError("If 'q' is selected, the value must be an integer.")
            # Convert q to an integer after validation
            q = int(q)

    except (ValueError, TypeError) as e:
        # Handle cases where input cannot be converted to the expected type or is invalid (like non-integer q when 'q' type is selected)
        result = f"Error: Invalid input. Please check your values. Details: {str(e)}"
    except Exception as e:
        # Catch any other potential unexpected errors during computation
        result = f"An unexpected error occurred during computation: {str(e)}"

    if problem == "lwe":
        lwe_params_kwargs = {
            'n_param': n,
            'q_final_param': q,
        }

        try:
            sigma_e = float(sigma_e_str)
            lwe_params_kwargs['sigma_e_param'] = sigma_e
            
            # Determine the secret key distribution (Xs) based on user selection
            lwe_params_kwargs['secret_key_dist_param'] = secret_key_dist_type.lower()
            if secret_key_dist_type.lower() == 'binary':
                if hamming_weight_str == "":
                    Xs = ND.UniformMod(2)
                else:
                    hamming_weight = int(hamming_weight_str)
                    Xs = ND.SparseBinary(hw=hamming_weight)
                    lwe_params_kwargs['hamming_weight_param'] = hamming_weight
            elif secret_key_dist_type.lower() == 'ternary':
                if hamming_weight_str == "":
                    Xs = ND.UniformMod(2)
                else:
                    hamming_weight = int(hamming_weight_str)
                    Xs = ND.SparseTernary(p=hamming_weight)
                    lwe_params_kwargs['hamming_weight_param'] = hamming_weight
            elif secret_key_dist_type.lower() == 'discretegaussian':
                # For DiscreteGaussian, sigma_s is required
                sigma_s = float(sigma_s_str)
                Xs = ND.DiscreteGaussian(stddev=sigma_s)
                lwe_params_kwargs['sigma_s_param'] = sigma_s
            else:
                # Handle case where an invalid distribution type is received
                raise ValueError("Invalid secret key distribution type selected.")
            
            if m_str == "":
                myLWE = LWE.Parameters(
                    n=n,
                    q=q,
                    Xs=Xs, # Use the determined secret key distribution
                    Xe=ND.DiscreteGaussian(stddev=sigma_e),
                )
            else:
                m = int(m_str)
                lwe_params_kwargs['m_param'] = m
                myLWE = LWE.Parameters(
                    n=n,
                    q=q,
                    Xs=Xs, # Use the determined secret key distribution
                    Xe=ND.DiscreteGaussian(stddev=sigma_e),
                    m=m, # Use the provided m value
                )

            rough = (rough_str.lower() == "true")
            lwe_params_kwargs['rough_param'] = rough

            if rough:
                computation_result = LWE.estimate.rough(myLWE, jobs=8)
            else:
                computation_result = LWE.estimate(myLWE, jobs=8)
            
            lwe_params_kwargs['result'] = str(computation_result.__str__())

            log_entry = LWEQueryLog(**lwe_params_kwargs)
            db.session.add(log_entry)
            db.session.commit()

            result = "Each attack provides the following bit security:\n"
            min_security = (None, None)
            for k in computation_result.keys():
                try:
                    bit_security = math.floor(math.log2(computation_result[k]['rop']))
                    result += f"{k} -> {bit_security}-bit security\n"
                    if min_security[1] is None or bit_security < min_security[1]:
                        min_security = (k, bit_security)
                except Exception as e:
                    result += f"{k} -> undefined\n"
            result += "---------------------------------------------\n"
            result += f"Bit-security is at most {min_security[1]}-bits"
            

        except (ValueError, TypeError) as e:
            # Handle cases where input cannot be converted to the expected type or is invalid (like non-integer q when 'q' type is selected)
            result = f"Error: Invalid input. Please check your values. Details: {str(e)}"
        except Exception as e:
            # Catch any other potential unexpected errors during computation
            result = f"An unexpected error occurred during computation: {str(e)}"
    elif problem == "ntru":
        ntru_params_kwargs = {
            'n_param': n,
            'q_final_param': q,
        }
        try:
            sigma_e = float(sigma_e_str)
            ntru_params_kwargs['sigma_e_param'] = sigma_e
            # Determine the secret key distribution (Xs) based on user selection
            ntru_params_kwargs['secret_key_dist_param'] = secret_key_dist_type.lower()
            if secret_key_dist_type.lower() == 'binary':
                if hamming_weight_str == "":
                    Xs = ND.UniformMod(2)
                else:
                    hamming_weight = int(hamming_weight_str)
                    Xs = ND.SparseBinary(hw=hamming_weight)
                    ntru_params_kwargs['hamming_weight_param'] = hamming_weight
            elif secret_key_dist_type.lower() == 'ternary':
                if hamming_weight_str == "":
                    Xs = ND.UniformMod(2)
                else:
                    hamming_weight = int(hamming_weight_str)
                    Xs = ND.SparseTernary(p=hamming_weight)
                    ntru_params_kwargs['hamming_weight_param'] = hamming_weight
            elif secret_key_dist_type.lower() == 'discretegaussian':
                # For DiscreteGaussian, sigma_s is required
                sigma_s = float(sigma_s_str)
                Xs = ND.DiscreteGaussian(stddev=sigma_s)
                ntru_params_kwargs['sigma_s_param'] = sigma_s
            else:
                # Handle case where an invalid distribution type is received
                raise ValueError("Invalid secret key distribution type selected.")

            # Assuming LWE and ND are defined in the imported 'estimator' module
            if m_str == "":
                myNTRUParams = NTRU.Parameters(
                    n=n,
                    q=q,
                    Xs=Xs, # Use the determined secret key distribution
                    Xe=ND.DiscreteGaussian(stddev=sigma_e),
                )
            else:
                m = int(m_str)
                ntru_params_kwargs['m_param'] = m
                myNTRUParams = NTRU.Parameters(
                    n=n,
                    q=q,
                    Xs=Xs, # Use the determined secret key distribution
                    Xe=ND.DiscreteGaussian(stddev=sigma_e),
                    m=m, # Use the provided m value
                )

            rough = (rough_str.lower() == "true")
            ntru_params_kwargs['rough_param'] = rough
            # Assuming NTRU.estimate.rough is available and works as expected
            if rough:
                computation_result = NTRU.estimate.rough(myNTRUParams, jobs=8)
            else:
                computation_result = NTRU.estimate(myNTRUParams, jobs=8)
            ntru_params_kwargs['result'] = str(computation_result)

            # Log the NTRU query
            log_entry = NTRUQueryLog(**ntru_params_kwargs)
            
            db.session.add(log_entry)
            db.session.commit()

            result = "Each attack provides the following bit security:\n"
            min_security = (None, None)
            for k in computation_result.keys():
                try:
                    bit_security = math.floor(math.log2(computation_result[k]['rop']))
                    result += f"{k} -> {bit_security}-bit security\n"
                    if min_security[1] is None or bit_security < min_security[1]:
                        min_security = (k, bit_security)
                except Exception as e:
                    result += f"{k} -> undefined\n"
            result += "---------------------------------------------\n"
            result += f"Bit-security is at most {min_security[1]}-bits"
        except (ValueError, TypeError) as e:
            # Handle cases where input cannot be converted to the expected type or is invalid (like non-integer q when 'q' type is selected)
            result = f"Error: Invalid input. Please check your values. Details: {str(e)}"
        except Exception as e:
            # Catch any other potential unexpected errors during computation
            result = f"An unexpected error occurred during computation: {str(e)}"
    elif problem == "sis":
        sis_params_kwargs = {
            'n_param': n,
            'q_final_param': q,
        }
        try:
            length_bound = float(length_bound_str)
            sis_params_kwargs['length_bound_param'] = length_bound
            
            if m_str == "":
                mySISParams = SIS.Parameters(
                    n=n,
                    q=q,
                    length_bound=length_bound,
                )
            else:
                m = int(m_str)
                sis_params_kwargs['m_param'] = m
                mySISParams = SIS.Parameters(
                    n=n,
                    q=q,
                    length_bound=length_bound,
                    m=m, # Use the provided m value
                )

            rough = (rough_str.lower() == "true")
            sis_params_kwargs['rough_param'] = rough
            if rough:
                computation_result = SIS.estimate.rough(mySISParams, jobs=8)
            else:
                computation_result = SIS.estimate(mySISParams, jobs=8)
            
            sis_params_kwargs['result'] = str(computation_result)
            # Log the SIS query
            log_entry = SISQueryLog(**sis_params_kwargs)
            db.session.add(log_entry)
            db.session.commit()

            result = "Each attack provides the following bit security:\n"
            min_security = (None, None)
            for k in computation_result.keys():
                try:
                    bit_security = math.floor(math.log2(computation_result[k]['rop']))
                    result += f"{k} -> {bit_security}-bit security\n"
                    if min_security[1] is None or bit_security < min_security[1]:
                        min_security = (k, bit_security)
                except Exception as e:
                    result += f"{k} -> undefined\n"
            result += "---------------------------------------------\n"
            result += f"Bit-security is at most {min_security[1]}-bits"
        except (ValueError, TypeError) as e:
            # Handle cases where input cannot be converted to the expected type or is invalid (like non-integer q when 'q' type is selected)
            result = f"Error: Invalid input. Please check your values. Details: {str(e)}"
        except Exception as e:
            # Catch any other potential unexpected errors during computation
            result = f"An unexpected error occurred during computation: {str(e)}"
    else:
        result = "not implemented"

    # Return the result as a JSON response.
    # jsonify serializes the Python dictionary into a JSON formatted response.
    return jsonify({'result': result})
